import json
import logging
from typing import Any, Dict, Generator, List, Optional

from .agent.registry import available_functions, tools_description
from .config import client

logger = logging.getLogger(__name__)
DEFAULT_MODEL_NAME = "x-ai/grok-4.1-fast"


def run_agent_conversation_stream(
    user_prompt: str,
    messages: Optional[List[Dict[str, Any]]] = None,
    session_generated_files: Optional[List[str]] = None,
) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
    """一个生成器：逐步向前端产出事件，使前端可以实时显示工具调用链路。

    事件类型(event) 约定：
      - user_message: {content}
      - model_plan:   {raw_message, tool_calls:[{id,name,arguments_json}]}
      - tool_start:   {tool_call_id, name, arguments}
      - tool_result:  {tool_call_id, name, status, result(raw_json), parsed(optional)}
      - model_message: {content}
      - final_answer: {content, generated_files, requires_follow_up}
      - error: {message}

    生成器最终 return 与 run_agent_conversation 相同结构的 dict。
    """
    internal_messages: List[Dict[str, Any]]
    if messages is None:
        system_prompt = (
            "你是一个专业的、友好的地理空间分析AI助手。"
            "你的任务是帮助用户分析地理数据。"
            "当用户的指令不明确或缺少执行工具所需的必要参数时，你必须向用户提问以澄清问题。回复时采用简洁明确的表达方式"
            "在调用任何工具之前，请确保所有必需的参数都已从用户那里获得。"
        )
        internal_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        logger.debug("[stream] 新会话，用户输入: %s", user_prompt)
        yield {"event": "user_message", "data": {"content": user_prompt}}
    else:
        internal_messages = messages[:]
        internal_messages.append({"role": "user", "content": user_prompt})
        logger.debug("[stream] 继续会话，历史消息数: %s", len(messages))
        yield {"event": "user_message", "data": {"content": user_prompt}}

    if session_generated_files is None:
        session_generated_files = []

    generated_files: List[str] = session_generated_files

    try:
        logger.debug("[stream] 调用LLM，消息数: %s", len(internal_messages))
        response = client.chat.completions.create(
            model=DEFAULT_MODEL_NAME,
            messages=internal_messages,
            tools=tools_description,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        while True:
            if not tool_calls:
                final_answer = response_message.content
                is_question = "?" in (final_answer or "") or "？" in (final_answer or "")
                unique_files = list(dict.fromkeys(generated_files))
                generated_files[:] = unique_files

                logger.debug("[stream] 获得最终回答，长度: %s", len(final_answer or ""))
                internal_messages.append({"role": "assistant", "content": final_answer})
                yield {"event": "final_answer", "data": {
                    "content": final_answer,
                    "generated_files": unique_files,
                    "requires_follow_up": is_question,
                    "messages": internal_messages,
                }}
                return {
                    "answer": final_answer,
                    "generated_files": unique_files,
                    "requires_follow_up": is_question,
                    "messages": internal_messages,
                }

            # 有工具调用计划
            plan = []
            for tc in tool_calls:
                try:
                    args_parsed = json.loads(tc.function.arguments)
                except Exception:  # noqa: BLE001
                    args_parsed = tc.function.arguments
                plan.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args_parsed,
                })
            internal_messages.append(response_message.model_dump())
            yield {"event": "model_plan", "data": {"tool_calls": plan}}

            for tc in tool_calls:
                func_name = tc.function.name
                try:
                    try:
                        func_args = json.loads(tc.function.arguments)
                    except Exception:  # noqa: BLE001
                        func_args = {}
                    yield {"event": "tool_start", "data": {"tool_call_id": tc.id, "name": func_name, "arguments": func_args}}

                    logger.debug("[stream] 工具调用: %s, 参数: %s", func_name, func_args)
                    target_fn = available_functions.get(func_name)
                    if not target_fn:
                        raise ValueError(f"未知函数: {func_name}")

                    # 为generate_analysis_report函数传递session_generated_files参数
                    if func_name == "generate_analysis_report":
                        func_args["session_generated_files"] = generated_files

                    raw_result = target_fn(**func_args)
                    try:
                        parsed = json.loads(raw_result)
                    except Exception:  # noqa: BLE001
                        parsed = {"status": "unknown", "raw": raw_result}

                    # 收集生成文件
                    if isinstance(parsed, dict):
                        for key, value in parsed.items():
                            if isinstance(value, str) and (
                                'path' in key
                                or value.lower().endswith(
                                    ('.png', '.jpg', '.jpeg', '.gif', '.shp', '.json', '.csv')
                                )
                            ):
                                generated_files.append(value)
                            if key == 'generated_files' and isinstance(value, list):
                                generated_files.extend(value)

                    internal_messages.append({
                        "tool_call_id": tc.id,
                        "role": "tool",
                        "name": func_name,
                        "content": raw_result,
                    })
                    yield {"event": "tool_result", "data": {
                        "tool_call_id": tc.id,
                        "name": func_name,
                        "status": parsed.get('status'),
                        "result": parsed,
                    }}
                except Exception as e:  # noqa: BLE001
                    logger.exception("[stream] 工具调用失败: %s", func_name)
                    error_payload = {"tool_call_id": tc.id, "name": func_name, "error": str(e)}
                    yield {"event": "tool_result", "data": error_payload}
                    internal_messages.append({
                        "tool_call_id": tc.id,
                        "role": "tool",
                        "name": func_name,
                        "content": json.dumps({"status": "error", "message": str(e)}),
                    })
                    break  # 失败后提前反馈给模型

            # 继续下一轮
            logger.debug("[stream] 工具执行完毕，反馈给LLM，历史消息数: %s", len(internal_messages))
            response = client.chat.completions.create(
                model=DEFAULT_MODEL_NAME,
                messages=internal_messages,
                tools=tools_description,
                tool_choice="auto",
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            if not tool_calls and response_message.content:
                # 先发一个模型中间回答（可能是澄清问题）
                internal_messages.append({"role": "assistant", "content": response_message.content})
                yield {"event": "model_message", "data": {"content": response_message.content}}
                # 再继续 while 循环顶部处理 final_answer 分支
    except Exception as e:  # noqa: BLE001
        unique_files = list(dict.fromkeys(generated_files))
        generated_files[:] = unique_files
        logger.exception("[stream] 发生异常")
        yield {"event": "error", "data": {"message": str(e)}}
        return {
            "answer": f"发生错误: {e}",
            "generated_files": unique_files,
            "requires_follow_up": False,
            "messages": internal_messages,
        }

# ==============================================================================
# 3. 主流程：与模型交互
# ==============================================================================
def run_agent_conversation(
    user_prompt: str,
    messages: Optional[List[Dict[str, Any]]] = None,
    session_generated_files: Optional[List[str]] = None,
):
    """
    运行一个可能包含多轮对话的Agent流程。

    :param user_prompt: 用户的当前请求字符串。
    :param messages: 之前的对话历史。如果为None，则开始一个新对话。
    :param session_generated_files: 在当前会话中已经生成的文件列表。
    :return: 一个字典，包含模型的回答、是否需要继续对话，以及当前的对话历史。
    """
    if session_generated_files is None:
        session_generated_files = []

    if messages is None:
        logger.info("[chat] 开启新对话，请求: %s", user_prompt)
        system_prompt = (
            "你是一个专业的、友好的地理空间分析AI助手。"
            "你的任务是帮助用户分析地理数据。"
            "当用户的指令不明确或缺少执行工具所需的必要参数时，你必须向用户提问以澄清问题。"
            "在调用任何工具之前，请确保所有必需的参数都已从用户那里获得。"
            "在调用 `generate_analysis_report` 时，你必须传入 `session_generated_files` 参数，其中包含本次对话中所有已生成文件的列表。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    else:
        logger.info("[chat] 继续对话，请求: %s", user_prompt)
        messages.append({"role": "user", "content": user_prompt})

    logger.debug("[chat] 当前消息数: %s", len(messages))
    response = client.chat.completions.create(
        model=DEFAULT_MODEL_NAME,
        messages=messages,
        tools=tools_description,
        tool_choice="auto",
    )
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    while True:
        if not tool_calls:
            final_answer = response_message.content
            # 检查这是否是一个问题
            is_question = "?" in final_answer or "？" in final_answer

            logger.debug("[chat] 返回最终回答，是否追问: %s", is_question)
            messages.append({"role": "assistant", "content": final_answer})
            unique_files = list(dict.fromkeys(session_generated_files))
            session_generated_files[:] = unique_files
            return {
                "answer": final_answer,
                "generated_files": unique_files,
                "requires_follow_up": is_question,
                "messages": messages
            }

        logger.debug("[chat] 模型计划调用 %s 个函数", len(tool_calls))
        # 将模型的工具调用决策添加到历史记录中
        messages.append(response_message.model_dump())
        
        # 执行所有工具调用
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            try:
                function_args = json.loads(tool_call.function.arguments)
                logger.debug("[chat] 执行函数 %s, 参数: %s", function_name, function_args)

                # 如果是报告生成函数，特殊处理，注入所有已生成的文件列表
                if function_name == 'generate_analysis_report':
                    function_args['session_generated_files'] = session_generated_files

                function_to_call = available_functions.get(function_name)
                
                if function_to_call:
                    function_response_str = function_to_call(**function_args)
                    response_data = json.loads(function_response_str)

                    # 收集所有输出的文件路径
                    for key, value in response_data.items():
                        if 'path' in key and isinstance(value, str):
                            session_generated_files.append(value)
                        elif key == 'generated_files' and isinstance(value, list):
                            session_generated_files.extend(value)
                    
                    if response_data.get("status") == "error":
                        logger.warning("[chat] 函数 %s 执行失败: %s", function_name, response_data.get('message'))
                    
                    # 将成功的工具执行结果添加到历史记录
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response_str,
                    })
                else:
                    raise ValueError(f"未知函数: {function_name}")

            except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
                # 如果参数解析失败或函数执行出错，向模型报告错误
                logger.exception("[chat] 调用函数 %s 时出错", function_name)
                error_message = f"Error calling function {function_name}: {str(e)}. Please check your arguments."
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps({"status": "error", "message": error_message}),
                })
                # 跳过本次循环中剩余的工具调用，让模型根据错误报告决定下一步
                break
        
        logger.debug("[chat] 工具执行结束，反馈LLM，累计消息数: %s", len(messages))
        response = client.chat.completions.create(
            model=DEFAULT_MODEL_NAME,
            messages=messages,
            tools=tools_description,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

# if __name__ == '__main__':
    # --- 模拟一个多轮对话场景 ---
    # 1. 用户发起一个不完整的请求
    initial_prompt = f"你好，请使用 'SRTP/20200101_binjiang_point.xlsx' 文件帮我对起点数据做个聚类分析。"
    
    # 2. 第一次调用agent
    conversation_history = None
    result = run_agent_conversation(initial_prompt, conversation_history)
    conversation_history = result['messages']

    # 3. 检查agent是否需要追问
    if result['requires_follow_up']:
        print("\n--- 需要用户提供更多信息 ---")
        # 4. 模拟用户回答问题
        user_response = "好的，请帮我分成5类。"
        
        # 5. 带着用户的回答和对话历史，再次调用agent
        result = run_agent_conversation(user_response, conversation_history)
        conversation_history = result['messages']

    # --- 最终结果 ---
    print("\n\n===== 对话结束 =====")
    if not result['requires_follow_up']:
        print(f"最终回答: {result['answer']}")
        if result['generated_files']:
            print(f"生成的文件: {result['generated_files']}")
    else:
        print(f"对话未完成，模型仍在提问: {result['answer']}")
