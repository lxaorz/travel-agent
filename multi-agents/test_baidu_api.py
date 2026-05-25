"""
百度地图API测试脚本
用于测试地理编码和公共交通路线规划功能
【已修复：路线步骤解析、字段名称错误】
"""
import os
import sys
import json
import requests

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def load_env():
    """加载环境变量"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        print("❌ 未找到.env文件")
        return None
    
    env_vars = {}
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def test_baidu_geo(ak, address, city="南京"):
    """测试百度地理编码API"""
    print(f"\n{'='*60}")
    print(f"🧪 测试地理编码API")
    print(f"{'='*60}")
    print(f"地址: {address}")
    print(f"城市: {city}")
    
    url = "https://api.map.baidu.com/geocoding/v3/"
    params = {
        "address": address,
        "city": city,
        "output": "json",
        "ak": ak
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        result = response.json()
        
        if result.get("status") == 0:
            location = result.get("result", {}).get("location", {})
            lat = location.get("lat")
            lng = location.get("lng")
            level = result.get("result", {}).get("level")
            
            print(f"✅ 地理编码成功!")
            print(f"   纬度: {lat}")
            print(f"   经度: {lng}")
            print(f"   精度: {level}")
            return f"{lat},{lng}"
        else:
            print(f"❌ 地理编码失败")
            print(f"   错误码: {result.get('status')}")
            print(f"   错误信息: {result.get('message')}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def test_baidu_transit(ak, origin, destination, city="南京"):
    """测试百度公共交通路线API【已修复】"""
    print(f"\n{'='*60}")
    print(f"🧪 测试公共交通路线API")
    print(f"{'='*60}")
    print(f"起点: {origin}")
    print(f"终点: {destination}")
    print(f"城市: {city}")
    
    url = "https://api.map.baidu.com/direction/v2/transit"
    params = {
        "origin": origin,
        "destination": destination,
        "origin_coord_type": "bd09ll",
        "destination_coord_type": "bd09ll",
        "ak": ak
    }
    
    try:
        response = requests.get(url, params=params, timeout=60)
        result = response.json()
        
        if result.get("status") == 0:
            routes = result.get("result", {}).get("routes", [])
            print(f"✅ 路线查询成功!")
            print(f"   找到 {len(routes)} 条路线")
            
            if routes:
                route = routes[0]
                duration = route.get("duration", 0) // 60
                distance = route.get("distance", 0) // 1000
                price = route.get("price", "未知")
                
                print(f"\n📋 推荐路线:")
                print(f"   预计时间: {duration} 分钟")
                print(f"   距离: {distance} 公里")
                print(f"   预计费用: {price} 元")
                
                steps = route.get("steps", [])
                print(f"\n🚇 路线详情:")
                step_count = 0

                # 【核心修复】正确解析百度地图steps嵌套结构
                for leg in steps:
                    if isinstance(leg, list):
                        for step in leg:
                            if step_count >= 10:
                                break
                            # 修复：字段名是 instructions 不是 instruction
                            instruction = step.get("instructions", "")
                            vehicle_info = step.get("vehicle_info", {})
                            line_name = vehicle_info.get("line_name", "")
                            
                            if line_name:
                                instruction = f"乘坐 {line_name} | {instruction}"
                            
                            if instruction:
                                step_count += 1
                                print(f"   {step_count}. {instruction}")
                    if step_count >= 10:
                        print("   ... 省略后续步骤")
                        break

                if step_count == 0:
                    print(f"   ⚠️ 未找到路线步骤信息")
            
            return True
        else:
            print(f"❌ 路线查询失败")
            print(f"   错误码: {result.get('status')}")
            print(f"   错误信息: {result.get('message')}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("🗺️ 百度地图API测试工具")
    print("="*60)
    
    # 加载环境变量
    env_vars = load_env()
    if not env_vars:
        print("❌ 无法加载环境变量")
        return
    
    baidu_ak = env_vars.get("BAIDU_AK", "")
    
    if not baidu_ak or baidu_ak == "your_baidu_api_key_here":
        print("❌ 请先在.env文件中配置百度地图API密钥")
        print("   前往 https://lbsyun.baidu.com/ 注册获取")
        return
    
    print(f"✅ 已加载API密钥: {baidu_ak[:10]}...")
    
    # 测试地理编码
    test_addresses = [
        "南京河海大学江宁校区",
        "南京师范大学仙林校区",
        "南京大学"
    ]
    
    coords = {}
    for addr in test_addresses:
        coord = test_baidu_geo(baidu_ak, addr)
        if coord:
            coords[addr] = coord
    
    # 测试公共交通路线
    if coords.get("南京河海大学江宁校区") and coords.get("南京师范大学仙林校区"):
        test_baidu_transit(
            baidu_ak,
            coords["南京河海大学江宁校区"],
            coords["南京师范大学仙林校区"],
            "南京"
        )
    
    print(f"\n{'='*60}")
    print("📊 测试完成")
    print("="*60)

if __name__ == "__main__":
    main()