#!/usr/bin/env python
"""
更新executor_agent.py中的占位符替换逻辑
"""
import re

# 读取文件
with open(r'd:\code\python\project\LLM\travel-agent\multi-agents\agent_nodes\executor_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找需要替换的部分
old_pattern = r'''            # 替换参数中的占位符：\{\{stepN_result\}\}
            import re
            processed_params = \{\}
            for key, value in params\.items\(\):
                if isinstance\(value, str\):
                    # 查找所有 \{\{stepN_result\}\} 模式
                    step_refs = re\.findall\(r'\\{\\{step\(\d\+\)_result\\}\\}', value\)
                    if step_refs:
                        # 替换每个引用
                        final_value = value
                        for step_idx in step_refs:
                            step_num = int\(step_idx\)
                            if step_num in step_results:
                                final_value = final_value\.replace\(f'\{\{{step\{step_num\}_result\}\}\}', step_results\[step_num\]\)
                        processed_params\[key\] = final_value
                    else:
                        processed_params\[key\] = value
                else:
                    processed_params\[key\] = value
            
            print\(f"\\n\{'='\*60\}"\)
            print\(f"📋 执行计划步骤 \{i\+1\}/\{len\(query_plan\)\}: \{tool_name\}"\)
            print\(f"\{'='\*60\}"\)
            print\(f"  描述: \{description\}"\)
            if processed_params != params:
                print\(f"  原始参数: \{params\}"\)
                print\(f"  处理后参数: \{processed_params\}"\)
            else:
                print\(f"  参数: \{processed_params\}"\)'''

new_pattern = '''            # 替换参数中的占位符：{{stepN_result}}
            import re
            processed_params = {}
            has_replacement = False
            
            for key, value in params.items():
                if isinstance(value, str):
                    # 查找所有 {{stepN_result}} 或 {stepN_result} 模式
                    step_refs = re.findall(r'\\{\\{step(\\d+)_result\\}\\}', value)
                    if not step_refs:
                        step_refs = re.findall(r'\\{step(\\d+)_result\\}', value)
                    
                    if step_refs:
                        # 替换每个引用
                        final_value = value
                        for step_idx in step_refs:
                            step_num = int(step_idx)
                            if step_num in step_results:
                                # 替换两种格式的占位符
                                final_value = final_value.replace(f'\\{{\\{{step{step_num}_result\\}}\\}}', step_results[step_num])
                                final_value = final_value.replace(f'\\{{step{step_num}_result\\}}', step_results[step_num])
                                has_replacement = True
                        processed_params[key] = final_value
                    else:
                        processed_params[key] = value
                else:
                    processed_params[key] = value
            
            print(f"\\n{{'='*60}}")
            print(f"📋 执行计划步骤 {i+1}/{len(query_plan)}: {tool_name}")
            print(f"{{'='*60}}")
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
                print(f"  参数: {processed_params}")'''

# 直接替换
old_section = '''            # 替换参数中的占位符：{{stepN_result}}
            import re
            processed_params = {}
            for key, value in params.items():
                if isinstance(value, str):
                    # 查找所有 {{stepN_result}} 模式
                    step_refs = re.findall(r'\\{\\{step(\\d+)_result\\}\\}', value)
                    if step_refs:
                        # 替换每个引用
                        final_value = value
                        for step_idx in step_refs:
                            step_num = int(step_idx)
                            if step_num in step_results:
                                final_value = final_value.replace(f'\\{{\\{{step{step_num}_result\\}}\\}}', step_results[step_num])
                        processed_params[key] = final_value
                    else:
                        processed_params[key] = value
                else:
                    processed_params[key] = value
            
            print(f"\\n{{'='*60}}")
            print(f"📋 执行计划步骤 {i+1}/{len(query_plan)}: {tool_name}")
            print(f"{{'='*60}}")
            print(f"  描述: {description}")
            if processed_params != params:
                print(f"  原始参数: {params}")
                print(f"  处理后参数: {processed_params}")
            else:
                print(f"  参数: {processed_params}")'''

new_section = '''            # 替换参数中的占位符：{{stepN_result}}
            import re
            processed_params = {}
            has_replacement = False
            
            for key, value in params.items():
                if isinstance(value, str):
                    # 查找所有 {{stepN_result}} 或 {stepN_result} 模式
                    step_refs = re.findall(r'\\{\\{step(\\d+)_result\\}\\}', value)
                    if not step_refs:
                        step_refs = re.findall(r'\\{step(\\d+)_result\\}', value)
                    
                    if step_refs:
                        # 替换每个引用
                        final_value = value
                        for step_idx in step_refs:
                            step_num = int(step_idx)
                            if step_num in step_results:
                                # 替换两种格式的占位符
                                final_value = final_value.replace(f'\\{{\\{{step{step_num}_result\\}}\\}}', step_results[step_num])
                                final_value = final_value.replace(f'\\{{step{step_num}_result\\}}', step_results[step_num])
                                has_replacement = True
                        processed_params[key] = final_value
                    else:
                        processed_params[key] = value
                else:
                    processed_params[key] = value
            
            print(f"\\n{{'='*60}}")
            print(f"📋 执行计划步骤 {i+1}/{len(query_plan)}: {tool_name}")
            print(f"{{'='*60}}")
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
                print(f"  参数: {processed_params}")'''

if old_section in content:
    content = content.replace(old_section, new_section)
    print("✅ 成功替换占位符处理逻辑")
else:
    print("❌ 未找到需要替换的部分")
    print("正在查找相似部分...")
    
    # 尝试找到包含"替换参数中的占位符"的部分
    if "替换参数中的占位符" in content:
        print("✅ 找到占位符处理部分")
        # 提取该部分
        start = content.find("            # 替换参数中的占位符")
        end = content.find("            try:", start)
        if end > start:
            old = content[start:end]
            print(f"找到部分长度: {len(old)} 字符")
            # 显示前后文
            print(f"\\n前80字符: {repr(old[:80])}")

# 保存文件
with open(r'd:\code\python\project\LLM\travel-agent\multi-agents\agent_nodes\executor_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 文件已保存")
