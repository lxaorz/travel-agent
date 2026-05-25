"""
测试百度API和agent调用逻辑
"""
import os
import sys
import asyncio

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 加载环境变量
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

def test_baidu_api():
    """测试百度API"""
    import requests
    
    BAIDU_AK = os.getenv("BAIDU_AK", "")
    BAIDU_GEO_URL = "https://api.map.baidu.com/geocoding/v3/"
    BAIDU_TRANSIT_URL = "https://api.map.baidu.com/direction/v2/transit"
    
    print("="*60)
    print("🧪 测试百度地图API")
    print("="*60)
    
    if not BAIDU_AK or BAIDU_AK == "your_baidu_api_key_here":
        print("❌ 未配置百度API密钥")
        return
    
    print(f"✅ 已配置API密钥: {BAIDU_AK[:10]}...")
    
    # 测试1：地理编码
    print("\n📍 测试1：地理编码")
    addresses = [
        ("南京河海大学江宁校区", "南京"),
        ("南京师范大学仙林校区", "南京"),
    ]
    
    coords = {}
    for address, city in addresses:
        params = {
            "address": address,
            "city": city,
            "output": "json",
            "ak": BAIDU_AK
        }
        response = requests.get(BAIDU_GEO_URL, params=params, timeout=30)
        result = response.json()
        
        if result.get("status") == 0:
            location = result.get("result", {}).get("location", {})
            lat = location.get("lat")
            lng = location.get("lng")
            coord = f"{lat},{lng}"
            coords[address] = coord
            print(f"✅ {address} -> {coord}")
        else:
            print(f"❌ {address} -> {result.get('message')}")
    
    # 测试2：公共交通路线
    print("\n🚇 测试2：公共交通路线")
    if len(coords) >= 2:
        origin = list(coords.values())[0]
        destination = list(coords.values())[1]
        
        params = {
            "origin": origin,
            "destination": destination,
            "origin_coord_type": "bd09ll",
            "destination_coord_type": "bd09ll",
            "ak": BAIDU_AK
        }
        
        response = requests.get(BAIDU_TRANSIT_URL, params=params, timeout=60)
        result = response.json()
        
        if result.get("status") == 0:
            routes = result.get("result", {}).get("routes", [])
            print(f"✅ 路线查询成功! 找到 {len(routes)} 条路线")
            
            if routes:
                route = routes[0]
                duration = route.get("duration", 0) // 60
                distance = route.get("distance", 0) // 1000
                price = route.get("price", "未知")
                
                print(f"\n📋 推荐路线:")
                print(f"   预计时间: {duration} 分钟")
                print(f"   距离: {distance} 公里")
                print(f"   预计费用: {price} 元")
        else:
            print(f"❌ 路线查询失败: {result.get('message')}")
    
    print("\n" + "="*60)

def test_agent_logic():
    """测试agent的调用逻辑"""
    import re
    
    print("\n🤖 测试agent调用逻辑")
    print("="*60)
    
    # 模拟R1返回的计划
    plan = {
        "query_plan": [
            {
                "tool": "gaode_geo",
                "params": {"address": "南京河海大学江宁校区", "city": "南京"},
                "description": "获取起点坐标"
            },
            {
                "tool": "gaode_geo",
                "params": {"address": "南京师范大学仙林校区", "city": "南京"},
                "description": "获取终点坐标"
            },
            {
                "tool": "gaode_transit",
                "params": {"origin": "{{step1_result}}", "destination": "{{step2_result}}", "city": "南京"},
                "description": "查询公共交通路线"
            }
        ]
    }
    
    # 模拟执行步骤
    step_results = {}
    
    for i, step in enumerate(plan["query_plan"]):
        tool_name = step.get("tool")
        params = step.get("params")
        description = step.get("description")
        
        print(f"\n📋 步骤 {i+1}: {tool_name}")
        print(f"   描述: {description}")
        
        # 处理占位符替换
        processed_params = {}
        for key, value in params.items():
            if isinstance(value, str):
                # 查找所有 {{stepN_result}} 模式
                step_refs = re.findall(r'\{\{step(\d+)_result\}\}', value)
                if step_refs:
                    # 替换每个引用
                    final_value = value
                    for step_idx in step_refs:
                        step_num = int(step_idx)
                        if step_num in step_results:
                            final_value = final_value.replace(f'{{{{step{step_num}_result}}}}', step_results[step_num])
                    processed_params[key] = final_value
                else:
                    processed_params[key] = value
            else:
                processed_params[key] = value
        
        if processed_params != params:
            print(f"   ⚠️ 参数被替换:")
            print(f"      原始: {params}")
            print(f"      替换后: {processed_params}")
        
        # 模拟工具执行
        if tool_name == "gaode_geo":
            # 模拟返回坐标
            observation = "31.920763596301068,118.79233114528282" if i == 0 else "32.11357452257716,118.91650723965746"
            print(f"   ✅ 返回: {observation}")
            step_results[i + 1] = observation
        elif tool_name == "gaode_transit":
            # 验证参数是否正确
            if processed_params.get("origin") and processed_params.get("destination"):
                if "," in str(processed_params.get("origin")) and "," in str(processed_params.get("destination")):
                    print(f"   ✅ 参数格式正确，可以调用百度API")
                else:
                    print(f"   ❌ 参数格式错误!")
                    print(f"      origin: {processed_params.get('origin')}")
                    print(f"      destination: {processed_params.get('destination')}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 百度地图API和Agent调用逻辑测试")
    print("="*60)
    
    test_baidu_api()
    test_agent_logic()
    
    print("\n✅ 测试完成!")
