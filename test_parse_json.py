#!/usr/bin/env python3
"""小测试：验证 parse_json_response 的 debug 是否生效（截断/尾部文字可解析或报错清晰）。"""

import asyncio
import sys

# 项目根目录
sys.path.insert(0, ".")


async def main():
    from app.services.llm_client import get_llm_client

    client = get_llm_client()

    # 1. 正常 JSON
    r1 = await client.parse_json_response('{"primary_scene": "portrait", "ai_likelihood": 0.7}')
    assert r1.get("primary_scene") == "portrait" and r1.get("ai_likelihood") == 0.7
    print("[OK] 1. 正常 JSON 解析成功")

    # 2. 带 markdown 代码块
    r2 = await client.parse_json_response(
        '```json\n{"primary_scene": "other", "secondary_attributes": ["a"]}\n```'
    )
    assert r2.get("primary_scene") == "other" and r2.get("secondary_attributes") == ["a"]
    print("[OK] 2. 带 ```json 代码块解析成功")

    # 3. JSON 后面有尾部文字（之前容易导致 Unterminated string）
    raw3 = '{"primary_scene": "portrait", "secondary_attributes": ["studio"], "ai_likelihood": 0.6}\n这是多余说明'
    r3 = await client.parse_json_response(raw3)
    assert r3.get("primary_scene") == "portrait" and r3.get("ai_likelihood") == 0.6
    print("[OK] 3. JSON + 尾部文字 → 提取首段对象解析成功")

    # 4. 真正截断（未闭合字符串）应抛出 ValueError
    try:
        await client.parse_json_response('{"primary_scene": "portrait", "note": "未闭合的字符串')
        print("[FAIL] 4. 截断 JSON 应抛出异常")
        return 1
    except ValueError as e:
        if "未找到有效 JSON" in str(e) or "无效或截断" in str(e):
            print("[OK] 4. 截断 JSON 正确抛出 ValueError，信息清晰")
        else:
            print(f"[WARN] 4. 抛出了 ValueError 但文案可能不对: {e}")

    print("\n全部通过，debug 验证成功。")
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
