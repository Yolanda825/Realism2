import sys
import os
import json
# 导入 SDK 库，假设 lib 在当前目录或 pythonpath 中
from lib.ai import api
# 配置初始化参数
app = "mhc"       # 应用标识
biz = "mhc_proj_1076_64b9"     # 业务标识
region = "starii"   # 区域：meitu, pre-meitu, starii, pre-starii
env = "outer"          # 环境
# 1. 初始化 MHC 客户端
cli = api.AiApi(app, biz, region, env=env)
# 2. 准备请求参数
imageUrl = "https://aigcp.meitudata.com/sys_kfpt/68e8bdffeeaf6rdo20xu753132"
params = {
    "parameter": {
        "nMask": True,
        "rsp_media_type": "url"
    }
}
# 3. 调用 AI 接口 (示例：mtvsod_async)
apiPath = "v1/sod_async"
# "v1/outsourcing_gateway_submit_async"
print(f"Adding task to {apiPath}...")
# 方式一：直接 Invoke 调用
# cli.invoke(imageUrl, params, apiPath)
# 方式二：异步任务提交 (RunAsync)
# 参数说明：
# - url_list: 图片列表 [{"url": "xxx"}]
# - params: 算法参数
# - path: 接口路径
# - task_type: 任务类型 ("mtlab", "inference", "workflow", "formula")

taskResult = cli.runAsync(
    [{"url": imageUrl}],
    params,
    apiPath,
    "mtlab"
)
print("Task Submit Result:", json.dumps(taskResult, indent=2))
# 4. 查询任务结果
if "data" in taskResult and "result" in taskResult["data"]:
    taskId = taskResult["data"]["result"]["id"]
    print(f"Querying result for Task ID: {taskId}")
    # 轮询查询结果（演示仅调用一次）
    result = cli.queryResult(taskId)
    print("Query Result:", json.dumps(result, indent=2))
