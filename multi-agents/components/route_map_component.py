"""
交互式路线地图组件 - Streamlit集成版本
可以直接在Streamlit页面中显示的交互式地图
"""
import folium
from streamlit.components.v1 import html
from folium import plugins
import os

def create_route_map_html(origin, destination, origin_name, destination_name, route_details, duration, distance, price):
    """创建交互式路线地图的HTML代码"""
    
    # 计算中心点
    center_lat = (origin[1] + destination[1]) / 2
    center_lng = (origin[0] + destination[0]) / 2
    
    # 创建地图
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=11,
        tiles='OpenStreetMap'
    )
    
    # 添加起点标记（红色）
    folium.Marker(
        [origin[1], origin[0]],
        popup=f'<b>📍 起点</b><br>{origin_name}',
        tooltip='起点',
        icon=folium.Icon(color='red', icon='play', prefix='fa')
    ).add_to(m)
    
    # 添加终点标记（绿色）
    folium.Marker(
        [destination[1], destination[0]],
        popup=f'<b>🏁 终点</b><br>{destination_name}',
        tooltip='终点',
        icon=folium.Icon(color='green', icon='flag-checkered', prefix='fa')
    ).add_to(m)
    
    # 如果有路线详情，添加路线
    if route_details and len(route_details) > 0:
        for detail in route_details:
            if 'path' in detail and len(detail['path']) > 0:
                path = detail['path']
                if detail.get('type') == 'walk':
                    # 步行路线用虚线
                    folium.PolyLine(
                        path,
                        color='gray',
                        weight=3,
                        opacity=0.6,
                        dash_array='5, 10'
                    ).add_to(m)
                elif '地铁' in detail.get('line', ''):
                    # 地铁用蓝色实线
                    folium.PolyLine(
                        path,
                        color='#238636',
                        weight=5,
                        opacity=0.8
                    ).add_to(m)
                elif '公交' in detail.get('line', '') or '大巴' in detail.get('line', ''):
                    # 公交用蓝色实线
                    folium.PolyLine(
                        path,
                        color='#1f77b4',
                        weight=5,
                        opacity=0.8
                    ).add_to(m)
    
    # 添加起点到终点的连线（备用）
    folium.PolyLine(
        [[origin[1], origin[0]], [destination[1], destination[0]]],
        color='blue',
        weight=2,
        opacity=0.3,
        dash_array='10, 10'
    ).add_to(m)
    
    # 适应地图范围
    if route_details and len(route_details) > 0:
        all_points = [[origin[1], origin[0]], [destination[1], destination[0]]]
        for detail in route_details:
            if 'path' in detail:
                all_points.extend([[p[1], p[0]] for p in detail['path']])
        if len(all_points) > 2:
            m.fit_bounds(all_points)
    
    # 添加地图控件
    folium.LayerControl().add_to(m)
    plugins.Fullscreen().add_to(m)
    plugins.MousePosition().add_to(m)
    
    # 获取HTML
    map_html = m._repr_html_()
    
    # 创建完整的HTML页面
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .route-map-container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                margin: 10px 0;
                overflow: hidden;
            }}
            .route-header {{
                background: linear-gradient(135deg, #238636 0%, #196c2e 100%);
                color: white;
                padding: 15px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .route-stats {{
                display: flex;
                gap: 20px;
            }}
            .stat {{
                text-align: center;
            }}
            .stat-value {{
                font-size: 1.3em;
                font-weight: bold;
            }}
            .stat-label {{
                font-size: 0.85em;
                opacity: 0.9;
            }}
            .route-info {{
                padding: 15px;
                background: #f8f9fa;
                border-top: 1px solid #e0e0e0;
            }}
            .route-steps {{
                max-height: 200px;
                overflow-y: auto;
            }}
            .step {{
                display: flex;
                align-items: flex-start;
                gap: 10px;
                padding: 10px;
                margin-bottom: 8px;
                background: white;
                border-radius: 8px;
                border-left: 4px solid #238636;
            }}
            .step-icon {{
                font-size: 1.2em;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #e8f5e9;
                border-radius: 50%;
            }}
            .step-content {{
                flex: 1;
            }}
            .step-line {{
                font-weight: bold;
                color: #238636;
                margin-bottom: 4px;
            }}
            .step-desc {{
                font-size: 0.9em;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="route-map-container">
            <div class="route-header">
                <div>
                    <i class="fas fa-map-marked-alt"></i> 
                    <strong>路线导航</strong>
                </div>
                <div class="route-stats">
                    <div class="stat">
                        <div class="stat-value">{duration}分钟</div>
                        <div class="stat-label">⏱️ 时间</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{distance}公里</div>
                        <div class="stat-label">📏 距离</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">约{price}元</div>
                        <div class="stat-label">💰 费用</div>
                    </div>
                </div>
            </div>
            <div style="height: 350px;">
                {map_html}
            </div>
            <div class="route-info">
                <strong>🚶 路线详情:</strong>
                <div class="route-steps">
    """
    
    # 添加路线步骤
    if route_details:
        for i, detail in enumerate(route_details[:10], 1):
            icon = "🚶" if detail.get('type') == 'walk' else "🚇" if '地铁' in detail.get('line', '') else "🚌"
            line_info = f"<div class='step-line'>【{detail.get('line', '')}】</div>" if detail.get('line') else ""
            full_html += f"""
                    <div class="step">
                        <div class="step-icon">{icon}</div>
                        <div class="step-content">
                            <div class="step-desc">{line_info}{detail.get('instruction', '')}</div>
                        </div>
                    </div>
            """
    
    full_html += """
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return full_html

def display_route_map_in_streamlit(origin, destination, origin_name, destination_name, 
                                   route_details, duration, distance, price, height=500):
    """
    在Streamlit页面中显示交互式路线地图
    
    参数:
        origin: (lng, lat) - 起点坐标
        destination: (lng, lat) - 终点坐标
        origin_name: str - 起点名称
        destination_name: str - 终点名称
        route_details: list - 路线详情列表
        duration: int - 预计时间（分钟）
        distance: int - 距离（公里）
        price: int - 费用（元）
        height: int - 地图高度（像素）
    """
    # 生成HTML
    map_html = create_route_map_html(
        origin, destination, origin_name, destination_name,
        route_details, duration, distance, price
    )
    
    # 在Streamlit中显示
    html(map_html, height=height, scrolling=True)
