"""
百度地图路线HTML生成脚本
生成交互式地图网页，可以在浏览器中查看
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
    """获取公共交通路线"""
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
            
            return route
        else:
            return None
    else:
        print(f"   ❌ 路线查询失败: {result.get('message')}")
        return None

def get_route_details(route):
    """获取路线详情字符串"""
    details = []
    step_count = 0
    
    steps = route.get("steps", [])
    for leg in steps:
        if isinstance(leg, list):
            for step in leg:
                if step_count >= 15:
                    break
                if isinstance(step, dict):
                    instruction = step.get("instructions", "")
                    vehicle_info = step.get("vehicle_info", {})
                    line_name = vehicle_info.get("line_name", "")
                    
                    if line_name:
                        details.append(f"{step_count + 1}. 乘坐 {line_name} - {instruction}")
                    else:
                        details.append(f"{step_count + 1}. {instruction}")
                    step_count += 1
        if step_count >= 15:
            break
    
    return details

def bd09_to_wgs84(lng, lat):
    """BD09坐标转换为WGS84坐标（近似转换）"""
    import math
    
    x = lng - 0.0065
    y = lat - 0.006
    z = math.sqrt(x*x + y*y) - 0.00002 * math.sin(y * math.pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * math.pi)
    wgs_lng = z * math.cos(theta)
    wgs_lat = z * math.sin(theta)
    return (wgs_lng, wgs_lat)

def generate_interactive_map(origin, destination, origin_name, destination_name, city, route_details, duration, distance, price):
    """生成交互式HTML地图"""
    print(f"\n🖼️  生成交互式地图...")
    
    # 坐标转换
    origin_wgs = bd09_to_wgs84(origin[0], origin[1])
    dest_wgs = bd09_to_wgs84(destination[0], destination[1])
    
    # 计算中心点
    center_lng = (origin_wgs[0] + dest_wgs[0]) / 2
    center_lat = (origin_wgs[1] + dest_wgs[1]) / 2
    
    # 生成HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>路线地图 - {city}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .info-bar {{
            display: flex;
            justify-content: center;
            gap: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }}
        .info-item {{
            text-align: center;
        }}
        .info-item .label {{
            color: #666;
            font-size: 0.9em;
        }}
        .info-item .value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .content {{
            display: flex;
            gap: 20px;
            padding: 20px;
        }}
        @media (max-width: 900px) {{
            .content {{
                flex-direction: column;
            }}
        }}
        #map {{
            flex: 2;
            height: 500px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .route-info {{
            flex: 1;
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            overflow-y: auto;
            max-height: 500px;
        }}
        .route-info h3 {{
            color: #333;
            margin-bottom: 15px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .step {{
            padding: 10px;
            margin-bottom: 8px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .step:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗺️ 路线规划</h1>
            <p>从 <strong>{origin_name}</strong> 到 <strong>{destination_name}</strong></p>
        </div>
        
        <div class="info-bar">
            <div class="info-item">
                <div class="label">⏱️ 预计时间</div>
                <div class="value">{duration} 分钟</div>
            </div>
            <div class="info-item">
                <div class="label">📏 距离</div>
                <div class="value">{distance} 公里</div>
            </div>
            <div class="info-item">
                <div class="label">💰 预计费用</div>
                <div class="value">约 {price} 元</div>
            </div>
        </div>
        
        <div class="content">
            <div id="map"></div>
            <div class="route-info">
                <h3>🚶 路线详情</h3>
"""
    
    # 添加路线步骤
    for step in route_details:
        html_content += f"        <div class='step'>{step}</div>\n"
    
    html_content += f"""
            </div>
        </div>
        
        <div class="footer">
            <p>📅 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>🗺️ 地图数据: OpenStreetMap</p>
        </div>
    </div>
    
    <script>
        // 初始化地图
        var map = L.map('map').setView([{center_lat}, {center_lng}], 11);
        
        // 添加地图图层
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        // 添加起点标记
        var originMarker = L.marker([{origin_wgs[1]}, {origin_wgs[0]}]).addTo(map)
            .bindPopup('<strong>📍 起点</strong><br>{origin_name}')
            .openPopup();
        
        // 添加终点标记
        var destMarker = L.marker([{dest_wgs[1]}, {dest_wgs[0]}]).addTo(map)
            .bindPopup('<strong>📍 终点</strong><br>{destination_name}');
        
        // 尝试画一条直线连接起点和终点
        var line = L.polyline([
            [{origin_wgs[1]}, {origin_wgs[0]}],
            [{dest_wgs[1]}, {dest_wgs[0]}]
        ], {{
            color: '#667eea',
            weight: 4,
            opacity: 0.7,
            dashArray: '10, 10'
        }}).addTo(map);
        
        // 适应地图范围
        map.fitBounds([
            [{origin_wgs[1]}, {origin_wgs[0]}],
            [{dest_wgs[1]}, {dest_wgs[0]}]
        ], {{padding: [50, 50]}});
    </script>
</body>
</html>
"""
    
    # 保存HTML文件
    filename = "route_map.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"   ✅ 交互式地图已保存: {filename}")
    print(f"   💡 提示: 请在浏览器中打开此文件查看地图")
    
    return filename

def main():
    print("="*60)
    print("🗺️  百度地图路线HTML生成器")
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
    
    # 获取路线
    route = test_baidu_transit(BAIDU_AK, origin, destination, city)
    
    if route:
        duration = route.get("duration", 0) // 60
        distance = route.get("distance", 0) // 1000
        price = route.get("price", "未知")
        
        # 获取路线详情
        route_details = get_route_details(route)
        
        # 打印路线详情
        print(f"\n🚶 路线详情:")
        for step in route_details:
            print(f"   {step}")
        
        # 生成交互式地图
        generate_interactive_map(
            origin, destination, 
            origin_name, destination_name, 
            city, 
            route_details,
            duration, distance, price
        )
        
        print(f"\n" + "="*60)
        print("✅ 完成！")
        print("   📁 文件已保存:")
        print("      - route_map.html (交互式地图)")
        print("   💡 使用方法:")
        print("      1. 双击打开 route_map.html")
        print("      2. 或在浏览器中打开该文件")
        print("="*60)

if __name__ == "__main__":
    main()
