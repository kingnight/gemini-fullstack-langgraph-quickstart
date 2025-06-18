import os

from agent.tools_and_schemas import SearchQueryList, Reflection
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.types import Send
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from tavily import TavilyClient
from utils.log import debug,info,error

from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from agent.configuration import Configuration
from agent.prompts import (
    get_current_date,
    query_writer_instructions,
    web_searcher_instructions,
    reflection_instructions,
    answer_instructions,
)
from agent.utils import (
    get_citations,
    get_research_topic,
    insert_citation_markers,
    resolve_urls,
)

load_dotenv()

if os.getenv("OPENROUTER_API_KEY") is None:
    raise ValueError("OPENROUTER_API_KEY is not set")

if os.getenv("TAVILY_API_KEY") is None:
    raise ValueError("TAVILY_API_KEY is not set")

# Initialize Tavily client
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Nodes
def generate_query(state: OverallState, config: RunnableConfig) -> QueryGenerationState:
    """LangGraph node that generates a search queries based on the User's question.

    Uses Gemini 2.0 Flash to create an optimized search query for web research based on
    the User's question.

    Args:
        state: Current graph state containing the User's question
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated query
    """
    debug(f"开始生成查询，当前状态: {state}")
    configurable = Configuration.from_runnable_config(config)

    # check for custom initial search query count
    if state.get("initial_search_query_count") is None:
        state["initial_search_query_count"] = configurable.number_of_initial_queries

    # init LLM through OpenRouter
    llm = ChatOpenAI(
        model=configurable.query_generator_model,
        temperature=1.0,
        max_retries=2,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )
    structured_llm = llm.with_structured_output(SearchQueryList)

    # Format the prompt with length constraints
    current_date = get_current_date()
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        number_queries=state["initial_search_query_count"],
    ) + "\n\n重要提示：每个查询的长度必须控制在400个字符以内，请确保查询简洁且包含关键信息。"

    # Generate the search queries
    result = structured_llm.invoke(formatted_prompt)

    # 验证并优化查询长度
    optimized_queries = []
    for query in result.query:
        if len(query) > 400:
            # 如果查询过长，尝试提取关键信息
            words = query.split()
            optimized_query = ""
            for word in words:
                if len(optimized_query + " " + word) <= 400:
                    optimized_query += " " + word if optimized_query else word
                else:
                    break
            optimized_queries.append({
                "query": optimized_query,
                "rationale": result.rationale
            })
        else:
            optimized_queries.append({
                "query": query,
                "rationale": result.rationale
            })

    debug(f"生成的查询列表: {optimized_queries}")
    debug(f"生成理由: {result.rationale}")
    return {
        "query_list": optimized_queries
    }


def continue_to_web_research(state: QueryGenerationState):
    """LangGraph node that sends the search queries to the web research node.

    This is used to spawn n number of web research nodes, one for each search query.
    """
    return [
        Send("web_research", {"search_query": query_item["query"], "id": int(idx)})
        for idx, query_item in enumerate(state["query_list"])
    ]


def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs web research using Tavily Search API.

    Executes a web search using Tavily Search API to gather relevant information.

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings

    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count, and web_research_results
    """
    debug(f"开始网络搜索，查询: {state['search_query']}")
    
    # 配置 Tavily 客户端
    configurable = Configuration.from_runnable_config(config)
    
    # 执行搜索
    search_result = tavily_client.search(
        query=state["search_query"],
        search_depth="advanced",  # 使用高级搜索以获得更相关的结果
        max_results=5,  # 限制结果数量
        include_raw_content=True  # 包含原始内容以便后续处理
    )
    
    debug(f"搜索到 {len(search_result['results'])} 条结果")
    
    # 处理搜索结果
    sources = []
    formatted_results = []
    for i, result in enumerate(search_result["results"], 1):
        # 从URL中提取域名作为label
        try:
            from urllib.parse import urlparse
            domain = urlparse(result["url"]).netloc
            # 移除www.前缀
            label = domain.replace("www.", "").split(".")[0]
        except:
            label = f"source{i}"
            
        # 添加来源
        sources.append({
            "value": result["url"],
            "short_url": f"[{i}]",
            "label": label
        })
        
        # 格式化结果
        formatted_result = f"{result['title']}\n\n{result['content']}\n\nSource: {result['url']}"
        formatted_results.append(formatted_result)
    
    return {
        "search_query": [state["search_query"]],
        "web_research_result": formatted_results,
        "sources_gathered": sources
    }


def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    """LangGraph node that identifies knowledge gaps and generates potential follow-up queries.

    Analyzes the current summary to identify areas for further research and generates
    potential follow-up queries. Uses structured output to extract
    the follow-up query in JSON format.

    Args:
        state: Current graph state containing the running summary and research topic
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated follow-up query
    """
    debug(f"开始反思，当前研究循环次数: {state.get('research_loop_count', 0)}")
    configurable = Configuration.from_runnable_config(config)
    # Increment the research loop count and get the reasoning model
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    reasoning_model = state.get("reasoning_model") or configurable.reasoning_model

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = reflection_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n\n---\n\n".join(state["web_research_result"]),
    )
    # init Reasoning Model
    llm = ChatOpenAI(
        model=reasoning_model,
        temperature=1.0,
        max_retries=2,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )
    result = llm.with_structured_output(Reflection).invoke(formatted_prompt)

    debug(f"反思结果 - 是否足够: {result.is_sufficient}")
    debug(f"知识差距: {result.knowledge_gap}")
    debug(f"后续查询: {result.follow_up_queries}")

    return {
        "is_sufficient": result.is_sufficient,
        "knowledge_gap": result.knowledge_gap,
        "follow_up_queries": result.follow_up_queries,
        "research_loop_count": state["research_loop_count"],
        "number_of_ran_queries": len(state["search_query"]),
    }


def evaluate_research(
    state: ReflectionState,
    config: RunnableConfig,
) -> OverallState:
    """LangGraph routing function that determines the next step in the research flow.

    Controls the research loop by deciding whether to continue gathering information
    or to finalize the summary based on the configured maximum number of research loops.

    Args:
        state: Current graph state containing the research loop count
        config: Configuration for the runnable, including max_research_loops setting

    Returns:
        String literal indicating the next node to visit ("web_research" or "finalize_summary")
    """
    configurable = Configuration.from_runnable_config(config)
    max_research_loops = (
        state.get("max_research_loops")
        if state.get("max_research_loops") is not None
        else configurable.max_research_loops
    )
    if state["is_sufficient"] or state["research_loop_count"] >= max_research_loops:
        return "finalize_answer"
    else:
        return [
            Send(
                "web_research",
                {
                    "search_query": follow_up_query,
                    "id": state["number_of_ran_queries"] + int(idx),
                },
            )
            for idx, follow_up_query in enumerate(state["follow_up_queries"])
        ]


def finalize_answer(state: OverallState, config: RunnableConfig):
    """LangGraph node that finalizes the research summary."""
    debug("开始生成最终答案")
    configurable = Configuration.from_runnable_config(config)
    reasoning_model = state.get("reasoning_model") or configurable.reasoning_model

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = answer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n---\n\n".join(state["web_research_result"]),
    )

    # init Reasoning Model through OpenRouter
    llm = ChatOpenAI(
        model=reasoning_model,
        temperature=0,
        max_retries=2,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )
    result = llm.invoke(formatted_prompt)

    debug(f"生成的答案长度: {len(result.content)}")

    # 获取唯一来源
    unique_sources = []
    seen_urls = set()
    for source in state["sources_gathered"]:
        if source["value"] not in seen_urls:
            seen_urls.add(source["value"])
            unique_sources.append(source)

    # 格式化答案和引用
    formatted_answer = result.content
    
    # 在正文中插入引用标记
    for source in unique_sources:
        # 查找包含该URL的句子
        sentences = formatted_answer.split('.')
        for i, sentence in enumerate(sentences):
            if source["value"] in sentence:
                # 在句子末尾添加引用标记
                sentences[i] = sentence.replace(source["value"], f"{source['short_url']}")
        formatted_answer = '.'.join(sentences)

    # 添加引用部分
    references = "\n\n## 引用来源\n"
    for source in unique_sources:
        references += f"{source['short_url']}: {source['value']}\n"

    final_answer = formatted_answer + references

    debug(f"最终使用的来源数量: {len(unique_sources)}")
    debug(f"结果: {final_answer}")
    debug(f"引用来源: {unique_sources}")

    return {
        **state,
        "messages": [
            *state["messages"],
            AIMessage(content=final_answer)
        ]
    }


# Create our Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)

# Define the nodes we will cycle between
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

# Set the entrypoint as `generate_query`
# This means that this node is the first one called
builder.add_edge(START, "generate_query")
# Add conditional edge to continue with search queries in a parallel branch
builder.add_conditional_edges(
    "generate_query", continue_to_web_research, ["web_research"]
)
# Reflect on the web research
builder.add_edge("web_research", "reflection")
# Evaluate the research
builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
# Finalize the answer
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent")
