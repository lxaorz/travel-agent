"""
Summarizer Agent - 负责整合结果生成最终回答
使用自己的上下文：summarizer_context
支持用户偏好个性化
支持流式输出
"""
from typing import Dict, Any, AsyncGenerator
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from config.settings import QWEN3_MODEL, QWEN3_API_BASE, DASHSCOPE_API_KEY, QWEN3_TEMPERATURE, STREAMING_ENABLED
from graph.state import GlobalState
from user_profile_manager import get_profile_manager


def _build_summarizer_inputs(state: GlobalState):
    user_query = state.get("user_query", "")
    planner_context = state.get("planner_context") or {}
    query_mode = planner_context.get("query_mode", "full") if planner_context else "full"
    destination = planner_context.get("destination", "") if planner_context else ""
    origin = planner_context.get("origin", "") if planner_context else ""
    travel_days = planner_context.get("travel_days", 0) if planner_context else 0
    budget = planner_context.get("budget", 0) if planner_context else 0
    travel_date = planner_context.get("travel_date", "") if planner_context else ""
    preferences = planner_context.get("preferences", []) if planner_context else []
    
    executor_context = state.get("executor_context") or {}
    tool_results = executor_context.get("tool_results", []) if executor_context else []
    rag_results_history = executor_context.get("rag_results_history", []) if executor_context else []
    
    summarizer_context = state.get("summarizer_context") or {
        "final_summary": None
    }
    
    profile_manager = get_profile_manager()
    user_preferences_str = profile_manager.format_profile_for_prompt()
    
    rag_results = "\n---\n".join(rag_results_history)
    
    tool_results_str = ""
    map_html_content = None
    for result in tool_results:
        if "error" in result:
            tool_results_str += f"【{result['tool']}】错误: {result['error']}\n"
        else:
            result_content = result.get('result', '')
            if '[MAP_HTML_START]' in result_content and '[MAP_HTML_END]' in result_content:
                start_idx = result_content.index('[MAP_HTML_START]') + len('[MAP_HTML_START]')
                end_idx = result_content.index('[MAP_HTML_END]')
                map_html_content = result_content[start_idx:end_idx].strip()
                result_content = result_content[:result_content.index('[MAP_HTML_START]')].strip()
            tool_results_str += f"【{result['tool']}】{result_content}\n"
    
    summarizer_context["map_html"] = map_html_content
    
    operation_hints = []
    if rag_results:
        operation_hints.append("✅ 已找到知识库信息")
    if tool_results_str:
        operation_hints.append("✅ 已查询MCP工具")
    
    mode_hint = "🔍 简单查询模式" if query_mode == "simple" else "🧠 完整规划模式"
    
    return {
        "user_query": user_query,
        "user_preferences_str": user_preferences_str,
        "query_mode": query_mode,
        "destination": destination,
        "origin": origin,
        "travel_days": travel_days,
        "budget": budget,
        "travel_date": travel_date,
        "preferences": preferences,
        "rag_results": rag_results,
        "tool_results_str": tool_results_str,
        "summarizer_context": summarizer_context,
        "operation_hints": operation_hints,
        "mode_hint": mode_hint
    }


async def summarizer_agent_node(state: GlobalState) -> Dict[str, Any]:
    print(f"\n{'='*60}")
    print("▶️ Summarizer Agent 开始执行")
    print(f"{'='*60}")
    
    inputs = _build_summarizer_inputs(state)
    
    print(f"📊 状态信息:")
    print(f"  query_mode: {inputs['query_mode']}")
    print(f"  工具执行结果数: {len(inputs.get('tool_results_str', ''))}")
    print(f"  RAG结果数: {len(inputs.get('rag_results', ''))}")
    
    llm = ChatOpenAI(
        model=QWEN3_MODEL,
        base_url=QWEN3_API_BASE,
        api_key=DASHSCOPE_API_KEY,
        temperature=QWEN3_TEMPERATURE
    )
    
    simple_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的旅游助手。根据用户的查询和收集到的信息，为用户提供友好、直接的回答。

{user_preferences}

请参考以下信息：
1. 用户的原始查询
2. 从知识库中检索到的相关信息
3. 天气等工具查询结果

重要规则：
- 请根据用户偏好调整推荐
- 如果知识库检索结果与用户查询的目的地不相关，请明确告知用户"我的知识库中暂时没有{{目的地}}的详细攻略"，然后提供其他可行的建议
- 绝对不要编造任何不存在的景点、酒店、价格等信息
- 如果有工具查询结果（如天气），优先使用工具查询结果
- 用友好、简洁的语气回答，直接针对用户的问题，不要生成完整的旅游规划。"""),
        ("human", """用户查询：{user_query}

知识库检索结果：
{rag_results}

工具执行结果：
{tool_results}

请直接回答用户的问题：""")
    ])
    
    full_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的旅游规划师。根据收集到的信息，为用户生成一份详细、友好、实用的旅游规划。

{user_preferences}

请参考以下信息：
1. 用户的原始查询
2. 从知识库中检索到的相关信息
3. 天气、交通、住宿等工具查询结果
4. 用户的兴趣和偏好
5. 用户不喜欢的事物

重要规则：
- 请根据用户偏好调整推荐
- 如果知识库检索结果与用户查询的目的地不相关，请明确告知用户"我的知识库中暂时没有{{目的地}}的详细攻略"
- 绝对不要编造任何不存在的景点、酒店、价格等信息
- 如果有工具查询结果，优先使用工具查询结果
- 对于没有信息的部分，明确说明"暂无相关信息"

请给出一个完整的旅游规划，包括：
- 简要的行程概述
- 每日行程建议（如果有天数信息）
- 交通建议
- 住宿推荐
- 注意事项
- 根据用户兴趣的特别推荐

请用友好、专业的语气回答，确保信息准确、实用。"""),
        ("human", """用户查询：{user_query}

目的地：{destination}
出发地：{origin}
旅行天数：{travel_days}
预算：{budget}
出发日期：{travel_date}
用户偏好：{preferences}

知识库检索结果：
{rag_results}

工具执行结果：
{tool_results}

请生成旅游规划：""")
    ])
    
    print(f"\n📝 开始生成回答，模式: {inputs['query_mode']}")
    print(f"📋 用户偏好已注入")
    
    if inputs["query_mode"] == "simple":
        print(f"  使用简单查询提示词")
        chain = simple_prompt | llm
        response = await chain.ainvoke({
            "user_query": inputs["user_query"],
            "user_preferences": inputs["user_preferences_str"],
            "rag_results": inputs["rag_results"],
            "tool_results": inputs["tool_results_str"]
        })
    else:
        print(f"  使用完整规划提示词")
        chain = full_prompt | llm
        response = await chain.ainvoke({
            "user_query": inputs["user_query"],
            "user_preferences": inputs["user_preferences_str"],
            "destination": inputs["destination"],
            "origin": inputs["origin"],
            "travel_days": inputs["travel_days"],
            "budget": inputs["budget"],
            "travel_date": inputs["travel_date"],
            "preferences": inputs["preferences"],
            "rag_results": inputs["rag_results"],
            "tool_results": inputs["tool_results_str"]
        })
    
    hints_str = f"{inputs['mode_hint']}\n"
    if inputs['operation_hints']:
        hints_str += "\n".join(inputs['operation_hints']) + "\n\n"
    
    final_answer = hints_str + response.content
    inputs["summarizer_context"]["final_summary"] = final_answer
    
    print(f"\n✅ Summarizer Agent 执行完成")
    print(f"  回答长度: {len(final_answer)} 字符")
    print(f"  下一步: 结束")
    print(f"{'='*60}\n")
    
    return {
        "summarizer_context": inputs["summarizer_context"],
        "current_agent": "summarizer",
        "next_agent": None,
        "is_complete": True
    }


async def stream_summarizer_response(state: GlobalState) -> AsyncGenerator[str, None]:
    """
    流式生成总结回答
    """
    print(f"\n{'='*60}")
    print("▶️ Summarizer Agent 开始流式输出")
    print(f"{'='*60}")
    
    inputs = _build_summarizer_inputs(state)
    
    llm = ChatOpenAI(
        model=QWEN3_MODEL,
        base_url=QWEN3_API_BASE,
        api_key=DASHSCOPE_API_KEY,
        temperature=QWEN3_TEMPERATURE,
        streaming=True
    )
    
    simple_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的旅游助手。根据用户的查询和收集到的信息，为用户提供友好、直接的回答。

{user_preferences}

请参考以下信息：
1. 用户的原始查询
2. 从知识库中检索到的相关信息
3. 天气等工具查询结果

重要规则：
- 请根据用户偏好调整推荐
- 如果知识库检索结果与用户查询的目的地不相关，请明确告知用户"我的知识库中暂时没有{{目的地}}的详细攻略"，然后提供其他可行的建议
- 绝对不要编造任何不存在的景点、酒店、价格等信息
- 如果有工具查询结果（如天气），优先使用工具查询结果
- 用友好、简洁的语气回答，直接针对用户的问题，不要生成完整的旅游规划。"""),
        ("human", """用户查询：{user_query}

知识库检索结果：
{rag_results}

工具执行结果：
{tool_results}

请直接回答用户的问题：""")
    ])
    
    full_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的旅游规划师。根据收集到的信息，为用户生成一份详细、友好、实用的旅游规划。

{user_preferences}

请参考以下信息：
1. 用户的原始查询
2. 从知识库中检索到的相关信息
3. 天气、交通、住宿等工具查询结果
4. 用户的兴趣和偏好
5. 用户不喜欢的事物

重要规则：
- 请根据用户偏好调整推荐
- 如果知识库检索结果与用户查询的目的地不相关，请明确告知用户"我的知识库中暂时没有{{目的地}}的详细攻略"
- 绝对不要编造任何不存在的景点、酒店、价格等信息
- 如果有工具查询结果，优先使用工具查询结果
- 对于没有信息的部分，明确说明"暂无相关信息"

请给出一个完整的旅游规划，包括：
- 简要的行程概述
- 每日行程建议（如果有天数信息）
- 交通建议
- 住宿推荐
- 注意事项
- 根据用户兴趣的特别推荐

请用友好、专业的语气回答，确保信息准确、实用。"""),
        ("human", """用户查询：{user_query}

目的地：{destination}
出发地：{origin}
旅行天数：{travel_days}
预算：{budget}
出发日期：{travel_date}
用户偏好：{preferences}

知识库检索结果：
{rag_results}

工具执行结果：
{tool_results}

请生成旅游规划：""")
    ])
    
    hints_str = f"{inputs['mode_hint']}\n"
    if inputs['operation_hints']:
        hints_str += "\n".join(inputs['operation_hints']) + "\n\n"
    
    yield hints_str
    
    if inputs["query_mode"] == "simple":
        chain = simple_prompt | llm
        async for chunk in chain.astream({
            "user_query": inputs["user_query"],
            "user_preferences": inputs["user_preferences_str"],
            "rag_results": inputs["rag_results"],
            "tool_results": inputs["tool_results_str"]
        }):
            if hasattr(chunk, 'content'):
                yield chunk.content
    else:
        chain = full_prompt | llm
        async for chunk in chain.astream({
            "user_query": inputs["user_query"],
            "user_preferences": inputs["user_preferences_str"],
            "destination": inputs["destination"],
            "origin": inputs["origin"],
            "travel_days": inputs["travel_days"],
            "budget": inputs["budget"],
            "travel_date": inputs["travel_date"],
            "preferences": inputs["preferences"],
            "rag_results": inputs["rag_results"],
            "tool_results": inputs["tool_results_str"]
        }):
            if hasattr(chunk, 'content'):
                yield chunk.content
