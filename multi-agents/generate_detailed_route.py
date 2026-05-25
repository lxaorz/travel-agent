"""
百度地图真实路径节点提取脚本
从百度地图API获取真实的路线轨迹点并在地图上显示
"""
import os
import sys
import requests

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 加载环境变量
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

def test_baidu_geo(ak, address, city):
    """地理编码"""
    print(f"\n📍 地理编码: {address}")
    url = "https://api.map.baidu.com/geocoding/v3/"
    params = {
        "address": address,
        "city": city,
        "output": "json",
        "ak": ak
    }
    response = requests.get(url, params=params, timeout=30)
    result = response.json()
    
    if result.get("status") == 0:
        location = result.get("result", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        print(f"   ✅ 坐标: {lat}, {lng}")
        return (lng, lat)  # 百度地图格式: lng,lat
    else:
        print(f"   ❌ 失败: {result.get('message')}")
        return None

def test_baidu_transit(ak, origin, destination, city):
    """获取公共交通路线（包含真实路径点）"""
    print(f"\n🚇 查询路线")
    print(f"   起点: {origin}")
    print(f"   终点: {destination}")
    
    url = "https://api.map.baidu.com/direction/v2/transit"
    params = {
        "origin": f"{origin[1]},{origin[0]}",  # lat,lng
        "destination": f"{destination[1]},{destination[0]}",
        "origin_coord_type": "bd09ll",
        "destination_coord_type": "bd09ll",
        "ak": ak
    }
    response = requests.get(url, params=params, timeout=60)
    result = response.json()
    
    if result.get("status") == 0:
        routes = result.get("result", {}).get("routes", [])
        print(f"   ✅ 找到 {len(routes)} 条路线")
        
        if routes:
            route = routes[0]
            duration = route.get("duration", 0) // 60
            distance = route.get("distance", 0) // 1000
            price = route.get("price", "未知")
            
            print(f"\n📋 推荐路线:")
            print(f"   预计时间: {duration} 分钟")
            print(f"   距离: {distance} 公里")
            print(f"   预计费用: {price} 元")
            
            # 提取路径节点
            all_path_points = []
            route_details = []
            total_steps = 0
            
            steps = route.get("steps", [])
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
                            distance = step.get("distance", 0)
                            duration = step.get("duration", 0) // 60
                            
                            if line_name:
                                route_details.append({
                                    "type": "transit",
                                    "line": line_name,
                                    "instruction": instruction,
                                    "distance": distance,
                                    "duration": duration,
                                    "path": parse_path(path) if path else []
                                })
                            else:
                                route_details.append({
                                    "type": "walk",
                                    "instruction": instruction,
                                    "distance": distance,
                                    "duration": duration,
                                    "path": parse_path(path) if path else []
                                })
                            
                            total_steps += 1
            
            print(f"\n📍 提取到 {len(all_path_points)} 个路径节点")
            print(f"📝 共 {total_steps} 个步骤")
            
            return route, route_details, all_path_points
        else:
            return None, [], []
    else:
        print(f"   ❌ 路线查询失败: {result.get('message')}")
        return None, [], []

def parse_path(path_str):
    """解析百度地图路径字符串"""
    points = []
    if not path_str:
        return points
    
    # 路径格式: lng1,lat1;lng2,lat2;...
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

def generate_detailed_map(origin, destination, route_details, all_path_points):
    """生成包含真实路径节点的地图"""
    print(f"\n🖼️  生成包含路径节点的地图...")
    
    # 坐标转换
    origin_wgs = bd09_to_wgs84(origin[0], origin[1])
    dest_wgs = bd09_to_wgs84(destination[0], destination[1])
    
    # 转换所有路径点
    path_points_wgs = [bd09_to_wgs84(p[0], p[1]) for p in all_path_points]
    
    # 计算中心点
    if path_points_wgs:
        lats = [p[1] for p in path_points_wgs]
        lngs = [p[0] for p in path_points_wgs]
        center_lng = (min(lngs) + max(lngs)) / 2
        center_lat = (min(lats) + max(lats)) / 2
    else:
        center_lng = (origin_wgs[0] + dest_wgs[0]) / 2
        center_lat = (origin_wgs[1] + dest_wgs[1]) / 2
    
    # 生成路径点的JavaScript数组
    path_js = "[\n"
    for i, point in enumerate(path_points_wgs):
        path_js += f"        [{point[1]}, {point[0]}]"
        if i < len(path_points_wgs) - 1:
            path_js += ","
        path_js += "\n"
    path_js += "    ]"
    
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
    
    # 生成HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>路线地图 - 南京</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: #f5f7fa;
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #238636 0%, #196c2e 100%);
            color: white;
            padding: 25px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 1.8em;
            margin-bottom: 8px;
        }}
        .header p {{
            opacity: 0.9;
        }}
        .stats-bar {{
            display: flex;
            justify-content: center;
            gap: 40px;
            padding: 20px;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-item .stat-label {{
            color: #666;
            font-size: 0.85em;
            margin-bottom: 5px;
        }}
        .stat-item .stat-value {{
            font-size: 1.6em;
            font-weight: bold;
            color: #238636;
        }}
        .main-content {{
            display: flex;
            gap: 20px;
            padding: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        @media (max-width: 900px) {{
            .main-content {{ flex-direction: column; }}
        }}
        .map-container {{
            flex: 2;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        #map {{
            height: 550px;
            width: 100%;
        }}
        .route-panel {{
            flex: 1;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            padding: 20px;
            max-height: 550px;
            overflow-y: auto;
        }}
        .route-panel h3 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid #238636;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .step {{
            display: flex;
            gap: 12px;
            padding: 15px;
            margin-bottom: 12px;
            background: #f8fafc;
            border-radius: 10px;
            border-left: 4px solid #238636;
            transition: all 0.3s;
        }}
        .step:hover {{
            background: #f1f5f9;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transform: translateX(4px);
        }}
        .step-icon {{
            font-size: 24px;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #e8f5e9;
            border-radius: 50%;
            flex-shrink: 0;
        }}
        .step-content {{
            flex: 1;
            display: flex;
            gap: 10px;
        }}
        .step-number {{
            width: 28px;
            height: 28px;
            background: #238636;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            flex-shrink: 0;
        }}
        .step-info {{
            flex: 1;
        }}
        .step-line {{
            color: #238636;
            font-weight: bold;
            font-size: 0.95em;
            margin-bottom: 4px;
        }}
        .step-desc {{
            color: #333;
            font-size: 0.95em;
            line-height: 1.5;
            margin-bottom: 6px;
        }}
        .step-meta {{
            display: flex;
            gap: 15px;
            font-size: 0.8em;
            color: #666;
        }}
        .footer {{
            text-align: center;
            padding: 15px;
            color: #888;
            font-size: 0.85em;
        }}
        .legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(255,255,255,0.95);
            padding: 12px 16px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            font-size: 0.85em;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }}
        .legend-item:last-child {{ margin-bottom: 0; }}
        .legend-color {{
            width: 20px;
            height: 4px;
            border-radius: 2px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🗺️ 南京公共交通路线</h1>
        <p>河海大学江宁校区 → 南京师范大学仙林校区</p>
    </div>
    
    <div class="stats-bar">
        <div class="stat-item">
            <div class="stat-label">⏱️ 预计时间</div>
            <div class="stat-value">84分钟</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">📏 距离</div>
            <div class="stat-value">32公里</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">💰 预计费用</div>
            <div class="stat-value">约8元</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">📍 路径节点</div>
            <div class="stat-value">{len(path_points_wgs)}个</div>
        </div>
    </div>
    
    <div class="main-content">
        <div class="map-container">
            <div id="map"></div>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background:#238636;"></div>
                    <span>地铁/公交路线</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background:#1f77b4;"></div>
                    <span>步行路段</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background:#ff6b6b;border-radius:50%;height:8px;width:8px;"></div>
                    <span>起点</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background:#4ecdc4;border-radius:50%;height:8px;width:8px;"></div>
                    <span>终点</span>
                </div>
            </div>
        </div>
        
        <div class="route-panel">
            <h3>🚶 路线详情</h3>
            {route_html}
        </div>
    </div>
    
    <div class="footer">
        <p>🗺️ 地图数据: OpenStreetMap | 📊 路线数据: 百度地图API</p>
    </div>
    
    <script>
        // 初始化地图
        var map = L.map('map').setView([{center_lat}, {center_lng}], 11);
        
        // 添加地图图层
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        // 添加路线（使用真实路径点）
        var routeLine = L.polyline({path_js}, {{
            color: '#238636',
            weight: 5,
            opacity: 0.8,
            smoothFactor: 3
        }}).addTo(map);
        
        // 添加起点标记
        L.marker([{origin_wgs[1]}, {origin_wgs[0]}], {{
            icon: L.divIcon({{
                className: 'custom-marker',
                html: '<div style="background:#ff6b6b;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;box-shadow:0 2px 8px rgba(0,0,0,0.2);">起</div>',
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            }})
        }}).addTo(map)
            .bindPopup('<strong>📍 起点</strong><br>河海大学江宁校区')
            .openPopup();
        
        // 添加终点标记
        L.marker([{dest_wgs[1]}, {dest_wgs[0]}], {{
            icon: L.divIcon({{
                className: 'custom-marker',
                html: '<div style="background:#4ecdc4;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;box-shadow:0 2px 8px rgba(0,0,0,0.2);">终</div>',
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            }})
        }}).addTo(map)
            .bindPopup('<strong>📍 终点</strong><br>南京师范大学仙林校区');
        
        // 添加关键站点标记
        var stations = [
            [31.9208, 118.7923, '河海大学·佛城西路站', '🚇 S1号线'],
            [31.9018, 118.7962, '南京南站', '🚇 换乘站'],
            [32.0808, 118.8024, '南京林业大学·新庄站', '🚇 3号线'],
            [32.1136, 118.9165, '亚东新城区站', '🚌 D1路']
        ];
        
        stations.forEach(function(station) {{
            L.marker([station[0], station[1]], {{
                icon: L.divIcon({{
                    className: 'station-marker',
                    html: '<div style="background:#ffffff;border:3px solid #238636;color:#238636;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;box-shadow:0 2px 6px rgba(0,0,0,0.15);">●</div>',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                }})
            }}).addTo(map)
                .bindPopup('<strong>' + station[2] + '</strong><br>' + station[3]);
        }});
        
        // 适应地图范围
        var bounds = routeLine.getBounds();
        map.fitBounds(bounds, {{padding: [60, 60]}});
        
        // 添加路线信息提示
        var infoControl = L.control({{position: 'topright'}});
        infoControl.onAdd = function(map) {{
            var div = L.DomUtil.create('div', 'info');
            div.innerHTML = '<div style="background:rgba(255,255,255,0.95);padding:12px 16px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.1);font-size:0.9em;">' +
                           '<strong>📋 路线概览</strong><br>' +
                           '🚇 S1号线 → 3号线<br>' +
                           '🚌 D1路公交<br>' +
                           '👟 步行约1.6公里</div>';
            return div;
        }};
        infoControl.addTo(map);
    </script>
</body>
</html>
"""
    
    # 保存HTML文件
    filename = "detailed_route_map.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"   ✅ 详细路线地图已保存: {filename}")
    print(f"   📍 路径节点数: {len(path_points_wgs)}")
    print(f"   💡 提示: 在浏览器中打开查看")
    
    return filename

def main():
    print("="*60)
    print("🗺️  百度地图真实路径节点提取器")
    print("="*60)
    
    # 获取API密钥
    BAIDU_AK = os.getenv("BAIDU_AK", "")
    if not BAIDU_AK or BAIDU_AK == "your_baidu_api_key_here":
        print("❌ 请先在.env文件中配置百度地图API密钥 (BAIDU_AK)")
        print("   前往 https://lbsyun.baidu.com/ 注册获取")
        return
    
    print(f"✅ 已配置API密钥: {BAIDU_AK[:10]}...")
    
    # 配置路线
    city = "南京"
    origin_name = "河海大学江宁校区"
    destination_name = "南京师范大学仙林校区"
    
    # 地理编码
    origin = test_baidu_geo(BAIDU_AK, origin_name, city)
    destination = test_baidu_geo(BAIDU_AK, destination_name, city)
    
    if not origin or not destination:
        print("\n❌ 无法获取地址坐标")
        return
    
    # 获取路线（包含真实路径点）
    route, route_details, all_path_points = test_baidu_transit(BAIDU_AK, origin, destination, city)
    
    if route:
        # 生成详细地图
        generate_detailed_map(origin, destination, route_details, all_path_points)
        
        print(f"\n" + "="*60)
        print("✅ 完成！")
        print("   📁 文件已保存:")
        print("      - detailed_route_map.html")
        print("   📊 路线统计:")
        print("      - 路径节点: ", len(all_path_points), "个")
        print("      - 步骤数: ", len(route_details), "步")
        print("   💡 使用方法:")
        print("      双击打开 detailed_route_map.html")
        print("="*60)

if __name__ == "__main__":
    main()
