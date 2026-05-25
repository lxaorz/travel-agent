"""
简化版MCP诊断脚本 - 直接测试MCP服务器连接
"""
import asyncio
import sys
import os

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

async def simple_diagnose():
    print("="*60)
    print("MCP服务器诊断")
    print("="*60)

    try:
        # 直接导入MCP管理器
        print("\n1. 正在导入MCP模块...")
        from agents.mcp import MCPServerSse
        print("   [OK] agents.mcp 模块导入成功")

        # 读取配置
        print("\n2. 读取服务器配置...")
        import json
        config_path = "config/servers_config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        print(f"   找到 {len(config.get('mcp_servers', []))} 个MCP服务器配置")

        # 测试每个服务器
        print("\n3. 测试MCP服务器连接...")
        from contextlib import AsyncExitStack

        async with AsyncExitStack() as exit_stack:
            for server_conf in config.get("mcp_servers", []):
                name = server_conf.get("name", "Unknown")
                url = server_conf.get("url", "")

                print(f"\n   测试: {name}")
                print(f"   URL: {url}")

                try:
                    server = await exit_stack.enter_async_context(
                        MCPServerSse(name=name, params={"url": url})
                    )
                    print(f"   [OK] {name} 连接成功")

                    # 列出工具
                    try:
                        tools = await server.list_tools()
                        print(f"   可用工具数: {len(tools)}")
                        if tools:
                            tool_names = [t.name if hasattr(t, 'name') else str(t) for t in tools[:5]]
                            print(f"   工具列表: {', '.join(tool_names)}")
                    except Exception as te:
                        print(f"   [WARN] 无法列出工具: {te}")

                except Exception as e:
                    print(f"   [FAIL] {name} 连接失败: {e}")

        print("\n" + "="*60)
        print("诊断完成")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] 诊断失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simple_diagnose())
