"""
Executor Agent - 双模式架构
- 简单模式：ReAct循环，LLM自主决策
- 复杂模式：Plan-then-Execute，先列计划再执行
使用自己的上下文：executor_context
"""
from typing import Dict, Any, List
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import folium
from streamlit.components.v1 import html as st_html
from folium import plugins
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from config.settings import (
    QWEN3_MODEL, QWEN3_API_BASE, DASHSCOPE_API_KEY, QWEN3_TEMPERATURE,
    R1_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, R1_TEMPERATURE
)
from config.prompts import REACT_THOUGHT_PROMPT
from graph.state import GlobalState
from tools.rag_tool import query_travel_knowledge
from tools.tool_registry import get_tools_description_for_llm

def bd09_to_wgs84(lng, lat):
    """BD09坐标转换为WGS84坐标"""
    import math
    x = lng - 0.0065
    y = lat - 0.006
    z = math.sqrt(x*x + y*y) - 0.00002 * math.sin(y * math.pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * math.pi)
    wgs_lng = z * math.cos(theta)
    wgs_lat = z * math.sin(theta)
    return (wgs_lng, wgs_lat)




async def execute_tool(tool_name: str, params: Dict, manager, 
                  destination: str, origin: str, travel_date: str) -> Any:
    """执行单个工具"""
    try:
        if tool_name == "rag_search":
            query = params.get("query", destination)
            return await query_travel_knowledge(query)
        
        elif tool_name == "gaode_weather":
            city = params.get("city", destination)
            return "天气预报功能暂时不可用（高德MCP服务器已禁用）。请在.env文件中配置百度地图API密钥（BAIDU_AK）以使用此功能。"
        
        elif tool_name == "gaode_geo":
            address = params.get("address", "")
            city = params.get("city", "南京")
            
            if not address:
                return "地理编码失败: 地址参数为空"
            
            from config.settings import BAIDU_AK, BAIDU_GEO_URL
            if BAIDU_AK and BAIDU_AK != "your_baidu_api_key_here":
                import requests
                import json
                try:
                    api_params = {
                        "address": address,
                        "city": city,
                        "output": "json",
                        "ak": BAIDU_AK
                    }
                    print(f"🔍 [gaode_geo] 调用百度地理编码API: address={address}, city={city}")
                    response = requests.get(BAIDU_GEO_URL, params=api_params, timeout=30)
                    result = response.json()
                    
                    if result.get("status") == 0:
                        location = result.get("result", {}).get("location", {})
                        lat = location.get("lat")
                        lng = location.get("lng")
                        if lat and lng:
                            coords = f"{lat},{lng}"
                            print(f"✅ [gaode_geo] 成功: {coords}")
                            return coords
                        print(f"⚠️ [gaode_geo] 成功但无坐标: {response.text}")
                        return f"地理编码成功但未获取到坐标: {response.text}"
                    error_msg = f"地理编码失败: status={result.get('status')}, message={result.get('message')}"
                    print(f"❌ [gaode_geo] {error_msg}")
                    return error_msg
                except Exception as e:
                    error_msg = f"百度地图API调用失败: {str(e)}"
                    print(f"❌ [gaode_geo] {error_msg}")
                    return error_msg
            return "地理编码功能暂时不可用。请在.env文件中配置百度地图API密钥（BAIDU_AK）以使用此功能。前往 https://lbsyun.baidu.com/ 注册获取。"
        
        elif tool_name == "gaode_poi_search":
            keywords = params.get("keywords", f"{destination} 景点")
            return "POI搜索功能暂时不可用（高德MCP服务器已禁用）。请在.env文件中配置百度地图API密钥（BAIDU_AK）以使用此功能。"
        
        elif tool_name == "gaode_hotel_search":
            keywords = params.get("keywords", f"{destination} 酒店")
            return "酒店搜索功能暂时不可用（高德MCP服务器已禁用）。请在.env文件中配置百度地图API密钥（BAIDU_AK）以使用此功能。"
        
        elif tool_name == "lucky_day":
            date = params.get("date", travel_date)
            return await manager.call_tool("bazi Server", "getChineseCalendar", date=date)
        
        elif tool_name == "gaode_transit":
            origin = params.get("origin", "")
            destination = params.get("destination", "")
            city = params.get("city", "")
            origin_name = params.get("origin_name", "起点")
            destination_name = params.get("destination_name", "终点")
            
            if not origin or not destination:
                return "公共交通路线查询失败: origin或destination参数为空"
            
            from config.settings import BAIDU_AK, BAIDU_TRANSIT_URL
            if BAIDU_AK and BAIDU_AK != "your_baidu_api_key_here":
                import requests
                
                # 解析路径的辅助函数
                def parse_path(path_str):
                    points = []
                    if not path_str:
                        return points
                    pairs = path_str.split(';')
                    for pair in pairs:
                        if pair:
                            coords = pair.split(',')
                            if len(coords) == 2:
                                try:
                                    points.append((float(coords[0]), float(coords[1])))
                                except:
                                    pass
                    return points
                
                try:
                    api_params = {
                        "origin": origin,
                        "destination": destination,
                        "origin_coord_type": "bd09ll",
                        "destination_coord_type": "bd09ll",
                        "ak": BAIDU_AK
                    }
                    print(f"🔍 [gaode_transit] 调用百度公共交通API: origin={origin}, destination={destination}, city={city}")
                    response = requests.get(BAIDU_TRANSIT_URL, params=api_params, timeout=60)
                    result = response.json()
                    
                    if result.get("status") == 0:
                        routes = result.get("result", {}).get("routes", [])
                        if routes:
                            route = routes[0]
                            duration = route.get("duration", 0) // 60
                            distance = route.get("distance", 0) // 1000
                            price = route.get("price", "未知")
                            
                            output = f"公共交通路线查询成功！\n"
                            output += f"推荐路线信息：\n"
                            output += f"预计时间：{duration}分钟\n"
                            output += f"距离：{distance}公里\n"
                            output += f"预计费用：{price}元\n\n"
                            
                            # 提取路径节点和路线详情（与 generate_detailed_route.py 一致）
                            all_path_points = []  # 收集所有路径点
                            route_details = []
                            total_steps = 0
                            
                            steps = route.get("steps", [])
                            if steps:
                                output += "路线详情：\n"
                                for leg in steps:
                                    if isinstance(leg, list):
                                        for step in leg:
                                            if isinstance(step, dict):
                                                # 提取路径点
                                                path = step.get("path", "")
                                                if path:
                                                    points = parse_path(path)
                                                    all_path_points.extend(points)
                                                
                                                # 提取步骤信息
                                                instruction = step.get("instructions", "")
                                                vehicle_info = step.get("vehicle_info", {})
                                                line_name = vehicle_info.get("line_name", "")
                                                step_distance = step.get("distance", 0)
                                                step_duration = step.get("duration", 0) // 60
                                                
                                                if line_name:
                                                    instruction_text = f"乘坐 {line_name} | {instruction}"
                                                    # 提取站点信息
                                                    start_stop = step.get("start_location", {}).get("name", "")
                                                    end_stop = step.get("end_location", {}).get("name", "")
                                                    route_details.append({
                                                        "type": "transit",
                                                        "line": line_name,
                                                        "instruction": instruction,
                                                        "distance": step_distance,
                                                        "duration": step_duration,
                                                        "path": points,
                                                        "start_stop": start_stop,
                                                        "end_stop": end_stop
                                                    })
                                                else:
                                                    instruction_text = instruction
                                                    route_details.append({
                                                        "type": "walk",
                                                        "instruction": instruction,
                                                        "distance": step_distance,
                                                        "duration": step_duration,
                                                        "path": points
                                                    })
                                                
                                                if instruction:
                                                    output += f"{total_steps + 1}. {instruction_text}\n"
                                                    total_steps += 1
                                
                                if total_steps == 0:
                                    output += "⚠️ 未找到路线步骤信息\n"
                            
                            print(f"✅ [gaode_transit] 成功: 找到{len(routes)}条路线, 推荐路线{duration}分钟, {distance}公里")
                            print(f"📍 提取到 {len(all_path_points)} 个路径节点")
                            print(f"📝 共 {total_steps} 个步骤")
                            
                            # 生成地图HTML（使用收集到的所有路径点）
                            try:
                                origin_coords = origin.split(',')
                                dest_coords = destination.split(',')
                                print(f"🔍 [地图调试] origin: {origin}, dest: {destination}")
                                print(f"🔍 [地图调试] all_path_points 数量: {len(all_path_points)}")
                                print(f"🔍 [地图调试] route_details 数量: {len(route_details) if route_details else 0}")
                                
                                if len(origin_coords) == 2 and len(dest_coords) == 2:
                                    origin_lat = float(origin_coords[0])
                                    origin_lng = float(origin_coords[1])
                                    dest_lat = float(dest_coords[0])
                                    dest_lng = float(dest_coords[1])
                                    
                                    # 坐标转换：BD09 -> WGS84
                                    origin_wgs = bd09_to_wgs84(origin_lng, origin_lat)
                                    dest_wgs = bd09_to_wgs84(dest_lng, dest_lat)
                                    
                                    # 转换所有路径点
                                    path_points_wgs = [bd09_to_wgs84(p[0], p[1]) for p in all_path_points]
                                    print(f"🔍 [地图调试] path_points_wgs 数量: {len(path_points_wgs)}")
                                    
                                    # 计算地图中心点
                                    if path_points_wgs:
                                        lats = [p[1] for p in path_points_wgs]
                                        lngs = [p[0] for p in path_points_wgs]
                                        center_lng = (min(lngs) + max(lngs)) / 2
                                        center_lat = (min(lats) + max(lats)) / 2
                                    else:
                                        center_lng = (origin_wgs[0] + dest_wgs[0]) / 2
                                        center_lat = (origin_wgs[1] + dest_wgs[1]) / 2
                                    print(f"🔍 [地图调试] 中心点: lat={center_lat}, lng={center_lng}")
                                    
                                    # 生成路径点的 JavaScript 数组（与 generate_detailed_route.py 完全一致）
                                    path_js = "[\n"
                                    for i, point in enumerate(path_points_wgs):
                                        path_js += f"        [{point[1]}, {point[0]}]"
                                        if i < len(path_points_wgs) - 1:
                                            path_js += ","
                                        path_js += "\n"
                                    path_js += "    ]"
                                    print(f"🔍 [地图调试] path_js 行数: {len(path_js.splitlines())}")
                                    
                                    # 生成中转节点的JavaScript代码
                                    transfer_nodes_js = ""
                                    if route_details and len(route_details) > 0:
                                        for i, detail in enumerate(route_details):
                                            if detail.get("type") == "transit" and detail.get("path") and len(detail["path"]) > 0:
                                                # 取该段路线的中间点作为站点位置
                                                path_points = detail["path"]
                                                mid_idx = len(path_points) // 2
                                                point = path_points[mid_idx]
                                                wgs_point = bd09_to_wgs84(point[0], point[1])
                                                line_name = detail.get("line", "")
                                                start_stop = detail.get("start_stop", "")
                                                end_stop = detail.get("end_stop", "")
                                                
                                                transfer_nodes_js += f"""
            L.marker([{wgs_point[1]}, {wgs_point[0]}], {{
                icon: L.divIcon({{
                    className: 'transfer-marker',
                    html: '<div style=\"background:#ff9800;color:white;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;box-shadow:0 2px 8px rgba(0,0,0,0.3);font-size:11px;\">{line_name[:4]}</div>',
                    iconSize: [32, 32],
                    iconAnchor: [16, 16]
                }})
            }}).addTo(map).bindPopup('<strong>🚇 {line_name}</strong><br>起点: {start_stop}<br>终点: {end_stop}');
                                                """
                                        print(f"🔍 [地图调试] 生成了 {len([d for d in route_details if d.get('type') == 'transit'])} 个中转节点")
                                    else:
                                        transfer_nodes_js = "// 无中转节点"
                                    
                                    # 生成路线详情HTML
                                    route_html = ""
                                    for i, detail in enumerate(route_details):
                                        icon = "🚶" if detail["type"] == "walk" else "🚇" if "地铁" in detail.get("line", "") else "🚌"
                                        line_info = f"【{detail['line']}】" if detail.get("line") else ""
                                        
                                        route_html += f"""
                                        <div class="step">
                                            <div class="step-icon">{icon}</div>
                                            <div class="step-content">
                                                <div class="step-number">{i + 1}</div>
                                                <div class="step-info">
                                                    <div class="step-line">{line_info}</div>
                                                    <div class="step-desc">{detail['instruction']}</div>
                                                    <div class="step-meta">
                                                        <span>📍 {detail['distance']}米</span>
                                                        <span>⏱️ {detail['duration']}分钟</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        """
                                    
                                    # 完整复制 generate_detailed_route.py 的地图 HTML
                                    map_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>路线地图</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f7fa; }}
        .map-container {{ position: relative; width: 100%; height: 500px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; }}
        #route-map {{ height: 100%; width: 100%; }}
        .legend {{
            position: absolute; bottom: 20px; left: 20px;
            background: rgba(255,255,255,0.95); padding: 12px 16px;
            border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            font-size: 0.85em; z-index: 1000;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
        .legend-color {{ width: 20px; height: 4px; border-radius: 2px; }}
    </style>
</head>
<body>
    <div class="map-container">
        <div id="route-map"></div>
        <div class="legend">
            <div class="legend-item"><div class="legend-color" style="background:#238636;"></div><span>地铁/公交路线</span></div>
            <div class="legend-item"><div class="legend-color" style="background:#1f77b4;"></div><span>步行路段</span></div>
            <div class="legend-item"><div class="legend-color" style="background:#ff6b6b;border-radius:50%;height:8px;width:8px;"></div><span>起点</span></div>
            <div class="legend-item"><div class="legend-color" style="background:#4ecdc4;border-radius:50%;height:8px;width:8px;"></div><span>终点</span></div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            var map = L.map('route-map').setView([{center_lat}, {center_lng}], 11);
            
            L.tileLayer('https://webrd0{{s}}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={{x}}&y={{y}}&z={{z}}', {{
                attribution: '© 高德地图',
                subdomains: ['1', '2', '3', '4']
            }}).addTo(map);
            
            var pathPoints = {path_js};
            if (pathPoints && pathPoints.length > 0) {{
                var routeLine = L.polyline(pathPoints, {{
                    color: '#238636',
                    weight: 5,
                    opacity: 0.8,
                    smoothFactor: 3
                }}).addTo(map);
                
                map.fitBounds(routeLine.getBounds(), {{padding: [60, 60]}});
            }}
            
            L.marker([{origin_wgs[1]}, {origin_wgs[0]}], {{
                icon: L.divIcon({{
                    className: 'custom-marker',
                    html: '<div style=\"background:#ff6b6b;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;box-shadow:0 2px 8px rgba(0,0,0,0.2);font-size:12px;\">起</div>',
                    iconSize: [28, 28],
                    iconAnchor: [14, 14]
                }})
            }}).addTo(map).bindPopup('<strong>📍 起点</strong><br>{origin_name}').openPopup();
            
            L.marker([{dest_wgs[1]}, {dest_wgs[0]}], {{
                icon: L.divIcon({{
                    className: 'custom-marker',
                    html: '<div style=\"background:#4ecdc4;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;box-shadow:0 2px 8px rgba(0,0,0,0.2);font-size:12px;\">终</div>',
                    iconSize: [28, 28],
                    iconAnchor: [14, 14]
                }})
            }}).addTo(map).bindPopup('<strong>📍 终点</strong><br>{{destination_name}}');
            
            // 添加中转节点标记
            {transfer_nodes_js}
            
            L.control.scale().addTo(map);
        }});
    </script>
</body>
</html>
                                    """
                                    
                                    print(f"🔍 [地图调试] 直接生成 map_html 长度: {len(map_html)}")
                                    output += f"\n\n[MAP_HTML_START]{map_html}[MAP_HTML_END]\n"
                            except Exception as map_err:
                                print(f"⚠️ 生成地图失败: {map_err}")
                                import traceback
                                traceback.print_exc()
                            
                            return output
                        else:
                            print(f"⚠️ [gaode_transit] 成功但无路线")
                            return "公共交通路线查询成功，但未找到可用路线"
                    error_msg = f"公共交通路线查询失败: status={result.get('status')}, message={result.get('message')}"
                    print(f"❌ [gaode_transit] {error_msg}")
                    return error_msg
                except Exception as e:
                    error_msg = f"百度地图API调用失败: {str(e)}"
                    print(f"❌ [gaode_transit] {error_msg}")
                    return error_msg
            return "公共交通路线查询功能暂时不可用。请在.env文件中配置百度地图API密钥（BAIDU_AK）以使用此功能。前往 https://lbsyun.baidu.com/ 注册获取。"
        
        elif tool_name == "train_query":
            from tools.mcp_tools import get_mcp_manager
            mgr = await get_mcp_manager()
            
            station_result = await mgr.call_tool(
                "12306 Server",
                "get-station-code-of-citys",
                citys=f"{origin},{destination}"
            )
            
            from_code = None
            to_code = None
            if station_result and "error" not in str(station_result).lower():
                codes_data = json.loads(station_result) if isinstance(station_result, str) else station_result
                if isinstance(codes_data, dict):
                    for city in [origin, destination]:
                        if city in codes_data and isinstance(codes_data[city], list) and len(codes_data[city]) > 0:
                            code = codes_data[city][0].get('station_code') or codes_data[city][0].get('code')
                            if city == origin:
                                from_code = code
                            else:
                                to_code = code
            
            if from_code and to_code:
                return await mgr.call_tool(
                    "12306 Server",
                    "get-tickets",
                    fromStation=from_code,
                    toStation=to_code,
                    date=travel_date
                )
            return "无法获取站点代码"
        
        return f"Unknown tool: {tool_name}"
    
    except Exception as e:
        return f"Tool execution failed: {str(e)}"


async def react_loop(state: GlobalState, planner_context: Dict, executor_context: Dict) -> Dict[str, Any]:
    """
    ReAct循环 - 简单模式：LLM自主决策
    
    核心逻辑：
    - 设置最大迭代次数作为安全限制
    - LLM每轮决定：继续收集信息 或 结束并生成答案
    - 只要LLM判断信息已充分，立即结束循环
    """
    print(f"\n{'='*60}")
    print("🔄 【简单模式】ReAct循环开始")
    print(f"{'='*60}")
    
    tool_results = executor_context.get("tool_results", [])
    rag_results_history = executor_context.get("rag_results_history", [])
    collected_info = executor_context.get("collected_info", {})
    
    destination = planner_context.get("destination", "")
    origin = planner_context.get("origin", "")
    travel_days = planner_context.get("travel_days", 0)
    budget = planner_context.get("budget", 0)
    travel_date = planner_context.get("travel_date", "")
    preferences = planner_context.get("preferences", [])
    user_query = state.get("user_query", "")
    
    from tools.mcp_tools import get_mcp_manager
    manager = await get_mcp_manager()
    
    qwen3_llm = ChatOpenAI(
        model=QWEN3_MODEL,
        base_url=QWEN3_API_BASE,
        api_key=DASHSCOPE_API_KEY,
        temperature=QWEN3_TEMPERATURE
    )
    
    # 最大迭代次数仅作为安全限制，防止死循环
    # LLM可以在任何时候决定提前结束
    max_iterations = 8
    iteration_count = 0
    
    print(f"\n📋 配置信息:")
    print(f"  最大迭代次数: {max_iterations} (仅作安全限制)")
    print(f"  LLM可随时判断信息充分并提前结束")
    
    while iteration_count < max_iterations:
        iteration_count += 1
        print(f"\n{'='*60}")
        print(f"🔄 ReAct迭代 {iteration_count}/{max_iterations}")
        print(f"{'='*60}")
        
        # 构建已收集信息
        collected_info_str = []
        
        # 显示已执行的工具列表（防止重复调用）
        if tool_results:
            collected_info_str.append("📋 已执行的工具：")
            executed_tools = set()
            for result in tool_results:
                tool_name = result.get("tool", "")
                if tool_name not in executed_tools:
                    executed_tools.add(tool_name)
                    collected_info_str.append(f"  • {tool_name}")
        
        # 显示RAG检索结果
        if rag_results_history:
            collected_info_str.append("\n📖 RAG检索结果：")
            for i, rag_result in enumerate(rag_results_history[-2:], 1):  # 只显示最近2个结果
                # 截取过长的内容
                truncated = rag_result[:300] + "..." if len(rag_result) > 300 else rag_result
                collected_info_str.append(f"  [结果{i}]: {truncated}")
        
        # 显示工具返回结果
        if tool_results:
            collected_info_str.append("\n🔧 工具返回结果：")
            for result in tool_results[-3:]:  # 只显示最近3个结果
                tool_name = result.get("tool", "")
                tool_result = str(result.get("result", ""))
                # 截取过长的内容
                truncated = tool_result[:500] + "..." if len(tool_result) > 500 else tool_result
                collected_info_str.append(f"  [{tool_name}]: {truncated}")
        
        if not collected_info_str:
            collected_info_str = "暂无信息"
        else:
            collected_info_str = "\n".join(collected_info_str)
        
        # 获取工具描述
        tools_desc = get_tools_description_for_llm()
        
        prompt = REACT_THOUGHT_PROMPT.format(
            user_query=user_query,
            destination=destination,
            origin=origin,
            travel_days=travel_days,
            budget=budget,
            travel_date=travel_date,
            preferences=preferences,
            collected_info=collected_info_str,
            iteration_count=iteration_count,
            max_iterations=max_iterations,
            available_tools=tools_desc
        )
        
        try:
            response = await qwen3_llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            print(f"\n🤖 LLM响应:")
            print(content[:500])
            
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end]
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end]
            
            if content.startswith("{"):
                brace_count = 0
                for i, char in enumerate(content):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            content = content[:i+1]
                            break
            
            decision = json.loads(content.strip())
            
            thought = decision.get("thought", "")
            action = decision.get("action", "")
            action_input = decision.get("action_input", {})
            should_continue = decision.get("continue", True)
            
            print(f"\n💡 思考: {thought}")
            print(f"🎯 决定行动: {action}")
            print(f"📝 行动参数: {action_input}")
            print(f"➡️  继续循环: {should_continue}")
            
            # 关键逻辑：只要LLM判断信息充分，立即结束循环
            # 不需要等待走完所有迭代次数
            if action == "final_answer" or not should_continue:
                print(f"\n✅ LLM判断信息已充分，提前结束ReAct循环")
                print(f"   已执行迭代: {iteration_count}/{max_iterations}")
                break
            
            # 🚨 额外保护：检查该工具是否已成功执行过（仅对非rag_search工具）
            tool_already_executed = False
            
            # 只对 MCP 工具（非 rag_search 做重复调用检查
            if action != "rag_search":
                for result in tool_results:
                    if result.get("tool") == action:
                        # 检查之前的执行是否成功（没有"失败"、"error"等关键词）
                        prev_result = str(result.get("result", ""))
                        if "失败" not in prev_result.lower() and "error" not in prev_result.lower() and "Tool execution failed" not in prev_result:
                            print(f"⚠️  工具 {action} 已成功执行过，跳过重复调用")
                            tool_already_executed = True
                            # 使用之前的结果
                            observation = prev_result
                            break
            
            if not tool_already_executed:
                print(f"\n🔧 执行工具: {action}")
                observation = await execute_tool(
                    action, action_input, manager,
                    destination, origin, travel_date
                )
                
                print(f"✅ 工具执行完成")
                
                tool_results.append({
                    "tool": action,
                    "result": observation,
                    "iteration": iteration_count
                })
                
                if action == "rag_search":
                    rag_results_history.append(str(observation))
                
                collected_info[action] = observation
            
        except Exception as e:
            print(f"❌ ReAct迭代异常: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print(f"\n{'='*60}")
    print(f"✅ ReAct循环结束 (实际执行: {iteration_count}次)")
    print(f"{'='*60}")
    
    # 更新自己的上下文
    executor_context["tool_results"] = tool_results
    executor_context["rag_results_history"] = rag_results_history
    executor_context["collected_info"] = collected_info
    
    return executor_context


async def plan_then_execute(state: GlobalState, planner_context: Dict, executor_context: Dict) -> Dict[str, Any]:
    """
    Plan-then-Execute - 复杂模式：先列计划再执行
    
    核心逻辑：
    - 先由 DeepSeek R1 制定详细的查询计划
    - 然后按计划依次执行每个步骤
    - 增加容错机制：某个工具失败不影响后续步骤
    - 完整执行完所有计划步骤（因为是预先规划好的）
    """
    print(f"\n{'='*60}")
    print("📋 【复杂模式】Plan-then-Execute开始")
    print(f"{'='*60}")
    
    destination = planner_context.get("destination", "")
    origin = planner_context.get("origin", "")
    travel_days = planner_context.get("travel_days", 0)
    budget = planner_context.get("budget", 0)
    travel_date = planner_context.get("travel_date", "")
    preferences = planner_context.get("preferences", [])
    user_query = state.get("user_query", "")
    
    tool_results = executor_context.get("tool_results", [])
    rag_results_history = executor_context.get("rag_results_history", [])
    collected_info = executor_context.get("collected_info", {})
    
    from tools.mcp_tools import get_mcp_manager
    manager = await get_mcp_manager()
    
    r1_llm = ChatOpenAI(
        model=R1_MODEL,
        base_url=DEEPSEEK_BASE_URL,
        api_key=DEEPSEEK_API_KEY,
        temperature=R1_TEMPERATURE
    )
    
    problem = f"""
用户的旅行需求：
最新查询：{user_query}

已提取的信息：
- 目的地：{destination}
- 出发地：{origin}
- 总天数：{travel_days}
- 总预算：{budget}元
- 出发日期：{travel_date}
- 偏好：{', '.join(preferences) if preferences else '无'}

请制定详细的查询计划，输出JSON格式：
{{
  "query_plan": [
    {{
      "tool": "工具名",
      "params": {{
        "参数名": "参数值，注意：如果需要使用前一步的结果，请使用{{{{stepN_result}}}}格式！"
      }},
      "description": "这一步的目的"
    }}
  ]
}}

可用工具：rag_search, gaode_weather, gaode_hotel_search, gaode_transit, gaode_geo, lucky_day, train_query

建议包含：
- rag_search：查询旅游攻略和景点信息
- gaode_weather：查询目的地天气
- gaode_geo：获取地点的经纬度坐标（格式：纬度,经度，例如：31.920763,118.792331）
- gaode_transit：查询公共交通路线（地铁+公交）【必须先调用gaode_geo获取坐标】
- gaode_hotel_search：搜索住宿
- lucky_day：查询黄历吉日
- train_query：查询火车票

🚨【重要】使用前一步结果的方法：
如果需要使用前一步的结果，请使用{{{{stepN_result}}}}格式，例如：
- 第1步调用gaode_geo获取起点坐标（{{{{step1_result}}}}）
- 第2步调用gaode_geo获取终点坐标（{{{{step2_result}}}}）
- 第3步调用gaode_transit时，origin参数值设为{{{{step1_result}}}}，destination参数值设为{{{{step2_result}}}}

🚨【重要】交通路线查询的正确流程：
如果用户询问"从A地到B地怎么走"或"如何从A到B"：
1. 首先调用 gaode_geo 获取A地的坐标，参数：{{"address": "A地名称", "city": "城市名"}}
2. 然后调用 gaode_geo 获取B地的坐标，参数：{{"address": "B地名称", "city": "城市名"}}
3. 最后调用 gaode_transit 查询路线，参数：{{"origin": "{{{{step1_result}}}}", "destination": "{{{{step2_result}}}}", "city": "城市名"}}
"""
    
    try:
        print(f"\n🧠 DeepSeek R1开始制定计划...")
        response = await r1_llm.ainvoke([HumanMessage(content=problem)])
        content = response.content.strip()
        
        print(f"\n📋 R1返回原始内容:")
        print(content[:500])
        
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                content = content[start:end]
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                content = content[start:end]

        # 清理JSON中的中文引号和其他问题
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace(''', "'").replace(''', "'")

        plan_data = json.loads(content.strip())
        query_plan = plan_data.get("query_plan", [])
        
        print(f"\n✅ 计划制定完成，共 {len(query_plan)} 步")
        print(f"   📝 说明：将完整执行所有计划步骤（预先规划好的）")
        for i, step in enumerate(query_plan):
            print(f"  步骤 {i+1}: {step.get('tool')} - {step.get('description')}")
        
        failed_steps = []
        step_results = {}  # 保存每一步的结果，格式 {step_number: result}
        
        for i, step in enumerate(query_plan):
            tool_name = step.get("tool", "")
            params = step.get("params", {})
            description = step.get("description", "")
            
            # 替换参数中的占位符：{{stepN_result}}
            import re
            processed_params = {}
            has_replacement = False
            
            for key, value in params.items():
                if isinstance(value, str):
                    # 查找所有 {{stepN_result}} 或 {stepN_result} 模式
                    step_refs = re.findall(r'\{\{step(\d+)_result\}\}', value)
                    if not step_refs:
                        step_refs = re.findall(r'\{step(\d+)_result\}', value)
                    
                    if step_refs:
                        # 替换每个引用
                        final_value = value
                        for step_idx in step_refs:
                            step_num = int(step_idx)
                            if step_num in step_results:
                                # 替换两种格式的占位符
                                final_value = final_value.replace('{{step' + str(step_num) + '_result}}', step_results[step_num])
                                final_value = final_value.replace('{step' + str(step_num) + '_result}', step_results[step_num])
                                has_replacement = True
                        processed_params[key] = final_value
                    else:
                        processed_params[key] = value
                else:
                    processed_params[key] = value
            
            print(f"\n{'='*60}")
            print(f"📋 执行计划步骤 {i+1}/{len(query_plan)}: {tool_name}")
            print(f"{'='*60}")
            print(f"  描述: {description}")
            print(f"  原始参数: {params}")
            if has_replacement or processed_params != params:
                print(f"  处理后参数: {processed_params}")
                if tool_name == "gaode_transit" and has_replacement:
                    origin_val = processed_params.get("origin", "")
                    dest_val = processed_params.get("destination", "")
                    if "," in str(origin_val) and "," in str(dest_val):
                        print(f"  ✅ 参数格式正确（包含逗号分隔的坐标）")
                    else:
                        print(f"  ⚠️ 警告：参数可能不是有效的坐标格式")
                        print(f"      origin: {origin_val}")
                        print(f"      destination: {dest_val}")
            else:
                print(f"  参数: {processed_params}")
            
            try:
                observation = await execute_tool(
                    tool_name, processed_params, manager,
                    destination, origin, travel_date
                )
                
                print(f"✅ 工具执行完成")
                
                tool_results.append({
                    "tool": tool_name,
                    "result": observation,
                    "step": description,
                    "success": True
                })
                
                if tool_name == "rag_search":
                    rag_results_history.append(str(observation))
                
                collected_info[tool_name] = observation
                
                # 保存这一步的结果，用于后续步骤的占位符替换
                if isinstance(observation, str):
                    step_results[i + 1] = observation
                
            except Exception as step_error:
                print(f"⚠️ 步骤执行失败: {step_error}")
                print(f"   继续执行后续步骤...")
                
                failed_steps.append({
                    "step": i + 1,
                    "tool": tool_name,
                    "error": str(step_error)
                })
                
                tool_results.append({
                    "tool": tool_name,
                    "result": f"工具执行失败: {str(step_error)}",
                    "step": description,
                    "success": False
                })
        
        if failed_steps:
            print(f"\n⚠️ 部分步骤执行失败 ({len(failed_steps)}/{len(query_plan)}):")
            for failed in failed_steps:
                print(f"  步骤 {failed['step']}: {failed['tool']} - {failed['error']}")
        
        print(f"\n✅ Plan-then-Execute 执行完成")
        print(f"   成功步骤: {len(query_plan) - len(failed_steps)}/{len(query_plan)}")
        
    except Exception as e:
        print(f"❌ Plan-then-Execute异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 更新自己的上下文
    executor_context["tool_results"] = tool_results
    executor_context["rag_results_history"] = rag_results_history
    executor_context["collected_info"] = collected_info
    
    return executor_context


async def executor_agent_node(state: GlobalState) -> Dict[str, Any]:
    """
    执行Agent节点 - 双模式选择
    使用自己的上下文：executor_context
    
    根据query_mode选择：
    - simple: ReAct循环，LLM自主决策
    - full: Plan-then-Execute，先列计划再执行
    """
    print(f"\n{'='*60}")
    print("▶️ Executor Agent 开始执行")
    print(f"{'='*60}")
    
    # 从 Planner 的上下文中获取信息
    planner_context = state.get("planner_context") or {}
    needs_deep_analysis = planner_context.get("needs_deep_analysis", False) if planner_context else False
    query_mode = planner_context.get("query_mode", "full") if planner_context else "full"
    
    # 初始化或获取自己的上下文
    executor_context = state.get("executor_context") or {
        "tool_results": [],
        "rag_results_history": [],
        "collected_info": {}
    }
    
    print(f"📊 状态信息:")
    print(f"  query_mode: {query_mode}")
    print(f"  needs_deep_analysis: {needs_deep_analysis}")
    
    if query_mode == "simple":
        print(f"\n✅ 【简单模式】ReAct循环，LLM自主决策")
        executor_context = await react_loop(state, planner_context, executor_context)
    else:
        print(f"\n✅ 【复杂模式】Plan-then-Execute，先列计划再执行")
        executor_context = await plan_then_execute(state, planner_context, executor_context)
    
    print(f"\n✅ Executor Agent 执行完成")
    print(f"  工具执行结果数: {len(executor_context.get('tool_results', []))}")
    print(f"  RAG结果数: {len(executor_context.get('rag_results_history', []))}")
    print(f"  下一步: summarizer")
    print(f"{'='*60}\n")
    
    return {
        "executor_context": executor_context,
        "current_agent": "executor",
        "next_agent": "summarizer"
    }
