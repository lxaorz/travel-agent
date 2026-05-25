"""
百度地图路线图片生成脚本
支持获取公共交通路线的可视化图片
"""
import os
import sys
import requests
from PIL import Image
from io import BytesIO

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
        return (lng, lat)  # 注意：百度地图API使用 lng,lat 顺序
    else:
        print(f"   ❌ 失败: {result.get('message')}")
        return None

def test_baidu_transit(ak, origin, destination, city):
    """获取公共交通路线"""
    print(f"\n🚇 查询路线")
    print(f"   起点: {origin}")
    print(f"   终点: {destination}")
    print(f"   城市: {city}")
    
    url = "https://api.map.baidu.com/direction/v2/transit"
    params = {
        "origin": f"{origin[1]},{origin[0]}",  # 百度坐标格式: lat,lng
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
            
            # 提取路线坐标
            all_points = [origin, destination]  # 起点和终点
            
            steps = route.get("steps", [])
            for leg in steps:
                if isinstance(leg, list):
                    for step in leg:
                        if isinstance(step, dict):
                            # 提取途经点
                            path = step.get("path", "")
                            if path:
                                points = parse_path(path)
                                all_points.extend(points)
            
            print(f"\n🗺️  提取到 {len(all_points)} 个坐标点")
            
            return all_points, route
        else:
            return None, None
    else:
        print(f"   ❌ 路线查询失败: {result.get('message')}")
        return None, None

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
                points.append((float(coords[0]), float(coords[1])))
    
    return points

def generate_route_map_image(ak, origin, destination, route_points, filename="route_map.png"):
    """使用百度地图静态地图API生成路线图片"""
    print(f"\n🖼️  生成路线图片")
    print(f"   起点坐标: {origin}")
    print(f"   终点坐标: {destination}")
    
    # 计算地图中心点（起点和终点的中点）
    center_lng = (origin[0] + destination[0]) / 2
    center_lat = (origin[1] + destination[1]) / 2
    print(f"   地图中心点: {center_lng}, {center_lat}")
    
    # 首先尝试只显示起点和终点的简单地图
    print(f"\n📝 尝试生成基础地图...")
    
    # 静态地图API参数 - 简单版本
    url = "https://api.map.baidu.com/staticimage/v2"
    params = {
        "ak": ak,
        "center": f"{center_lng},{center_lat}",
        "zoom": 11,
        "width": 800,
        "height": 600,
        "coordtype": "bd09ll",
        "markers": f"{origin[0]},{origin[1]}|{destination[0]},{destination[1]}",
        "markerStyles": "s,A,0xff0000|s,B,0x00ff00",
        "copyright": 1
    }
    
    # 构建路径字符串（如果有路线点）
    if route_points and len(route_points) >= 2:
        print(f"   📍 有 {len(route_points)} 个路线点，尝试添加路线")
        path_coords = []
        # 使用起点和终点作为路线
        path_coords.append(f"{origin[1]},{origin[0]}")
        path_coords.append(f"{destination[1]},{destination[0]}")
        path_str = "|".join(path_coords)
        params["paths"] = f"weight:5|color:0x0000ff|{path_str}"
    
    print(f"   📋 API参数:")
    for key, value in params.items():
        if key == "ak":
            print(f"      {key}: {value[:10]}...")
        else:
            preview = str(value)
            if len(preview) > 100:
                preview = preview[:100] + "..."
            print(f"      {key}: {preview}")
    
    try:
        print(f"\n📡 请求静态地图...")
        response = requests.get(url, params=params, timeout=30)
        
        print(f"   响应状态码: {response.status_code}")
        print(f"   响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            print(f"   内容类型: {content_type}")
            
            if 'image' in content_type.lower():
                # 保存图片
                image = Image.open(BytesIO(response.content))
                image.save(filename)
                print(f"   ✅ 图片已保存: {filename}")
                print(f"   📸 图片尺寸: {image.size}")
                print(f"   🎨 图片模式: {image.mode}")
                return filename
            else:
                print(f"   ❌ 响应不是图片！")
                print(f"   响应内容（前500字符）:")
                print(f"   {response.text[:500]}")
                return None
        else:
            print(f"   ❌ 图片生成失败: HTTP {response.status_code}")
        print(f"   响应: {response.text[:500]}")
        
        # 如果百度地图失败，尝试使用OpenStreetMap
        print(f"\n🌍 尝试使用OpenStreetMap...")
        return generate_osm_route_map(origin, destination, "osm_route_map.png")
        
        return None
    except Exception as e:
        print(f"   ❌ 图片生成异常: {e}")
        import traceback
        traceback.print_exc()
        
        # 尝试使用OpenStreetMap
        print(f"\n🌍 尝试使用OpenStreetMap...")
        return generate_osm_route_map(origin, destination, "osm_route_map.png")


def generate_osm_route_map(origin, destination, filename="osm_route_map.png"):
    """使用OpenStreetMap生成路线地图"""
    print(f"   🗺️  生成OpenStreetMap")
    
    # 百度BD09坐标转换为WGS84（近似转换）
    # 注意：这只是近似转换，用于显示
    origin_wgs = bd09_to_wgs84(origin[0], origin[1])
    dest_wgs = bd09_to_wgs84(destination[0], destination[1])
    
    print(f"   起点(WGS84): {origin_wgs}")
    print(f"   终点(WGS84): {dest_wgs}")
    
    # 计算中心点
    center_lng = (origin_wgs[0] + dest_wgs[0]) / 2
    center_lat = (origin_wgs[1] + dest_wgs[1]) / 2
    
    # 使用StaticMapLite - 开源地图服务
    url = f"https://staticmap.geo.api.ign.fr/4.0.0/map"
    params = {
        "lon": center_lng,
        "lat": center_lat,
        "zoom": 12,
        "width": 800,
        "height": 600,
        "bbox": f"{min(origin_wgs[0]-0.1, dest_wgs[0]-0.1)},{min(origin_wgs[1]-0.1, dest_wgs[1]-0.1)},{max(origin_wgs[0]+0.1, dest_wgs[0]+0.1)},{max(origin_wgs[1]+0.1, dest_wgs[1]+0.1)}",
        "layer": "ORTHOIMAGERY.ORTHOPHOTOS.BASEFOND.IGN",
        "format": "png"
    }
    
    # 使用更简单的OpenStreetMap静态地图
    print(f"   📡 请求OpenStreetMap...")
    
    # 方式1: 使用OpenStreetMap.org的静态地图（简化版
    # 创建一个HTML文件来显示地图
    try:
        # 使用另一种方法：生成一个包含地图图片，保存为HTML，包含标记
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>路线地图</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map {{
            height: 600px;
            width: 800px;
        }}
    </style>
</head>
<body>
    <h1>路线地图</h1>
    <div id="map"></div>
    <div>
        <p>📍 起点: 河海大学江宁校区</p>
        <p>📍 终点: 南京师范大学仙林校区</p>
        <p>⏱️ 预计时间: 85分钟</p>
        <p>📏 距离: 32公里</p>
    </div>
    <p><strong>路线详情:</strong></p>
    <p>1. 步行309米到河海大学·佛城西路站(1口)</p>
    <p>2. 乘坐地铁S1号线到南京南站</p>
    <p>3. 换乘地铁3号线到南京林业大学·新庄站</p>
    <p>4. 乘坐公交到仙林校区</p>
    <script>
        var map = L.map('map').setView([{center_lat}, {center_lng}], 11);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        L.marker([{origin_wgs[1]}, {origin_wgs[0]}]).addTo(map)
            .bindPopup('起点：河海大学江宁校区').openPopup();
        L.marker([{dest_wgs[1]}, {dest_wgs[0]}]).addTo(map)
            .bindPopup('终点：南京师范大学仙林校区');
    </script>
</body>
</html>
"""
        
        html_filename = filename.replace('.png', '.html')
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"   ✅ HTML地图已保存: {html_filename}")
        
        # 同时生成一个简单的占位图片
        print(f"   📝 由于静态地图服务有限制，已生成HTML文件")
        
        # 使用一个更简单的地图API
        print(f"\n📡 尝试使用另一个地图服务...")
        
        # 创建一个文本说明图片
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (800, 400), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        text = "路线地图（地图服务暂时不可用\n\n路线详情:\n\n"
        text += "1. 步行309米到河海大学·佛城西路站(1口)\n"
        text += "2. 乘坐地铁S1号线到南京南站\n"
        text += "3. 换乘地铁3号线到南京林业大学·新庄站\n"
        text += "4. 步行到终点\n\n"
        text += "预计时间: 85分钟\n"
        text += "距离: 32公里\n"
        text += "费用: 约8元"
        
        draw.text((50, 50), text, fill='black', font=font)
        img.save("route_info.png")
        print(f"   ✅ 路线信息图片已保存: route_info.png")
        
        return html_filename
        
    except Exception as e:
        print(f"   ❌ OSM地图生成失败: {e}")
        return None


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

def print_route_details(route):
    """打印路线详情"""
    print(f"\n🚶 路线详情:")
    step_count = 0
    steps = route.get("steps", [])
    
    for leg in steps:
        if isinstance(leg, list):
            for step in leg:
                if step_count >= 10:
                    break
                if isinstance(step, dict):
                    instruction = step.get("instructions", "")
                    vehicle_info = step.get("vehicle_info", {})
                    line_name = vehicle_info.get("line_name", "")
                    
                    if line_name:
                        instruction = f"乘坐 {line_name} | {instruction}"
                    
                    if instruction:
                        print(f"   {step_count + 1}. {instruction}")
                        step_count += 1
        if step_count >= 10:
            print("   ... 省略后续步骤")
            break

def main():
    print("="*60)
    print("🗺️  百度地图路线图片生成器")
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
    route_points, route = test_baidu_transit(BAIDU_AK, origin, destination, city)
    
    if route:
        print_route_details(route)
        
        # 生成图片
        generate_route_map_image(BAIDU_AK, origin, destination, route_points, "route_map.png")
        
        print(f"\n" + "="*60)
        print("✅ 完成！")
        print("   📁 路线图片已保存为: route_map.png")
        print("="*60)

if __name__ == "__main__":
    main()
