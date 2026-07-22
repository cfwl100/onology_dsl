#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
import urllib.parse
import requests
import argparse


def search_location(query, lng=None, lat=None, radius=10000, language="en"):
    """华为地图位置搜索"""

    # API配置
    api_key = "DAEDACIowRf+ogo1yxeyr+FtqKU0BgibFfePafHkroVkGrR+9H2yyloNgWsfA35HR+9/gLQYix3XaqgefX2HRZoStYzLq4uhMEozzg=="
    url = f"https://siteapi.cloud.huawei.com/mapApi/v1/siteService/searchByText?key={urllib.parse.quote(api_key, safe='')}"

    # 请求头
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # 请求体
    payload = {
        "query": query,
        "radius": radius,
        "language": language
    }

    # 如果提供了经纬度，添加到请求中
    if lng is not None and lat is not None:
        payload["location"] = {
            "lng": lng,
            "lat": lat
        }

    # 发送请求
    response = requests.post(url, json=payload, headers=headers)

    return response.json()

if __name__ == "__main__":
    # 1. 定义命令行参数
    parser = argparse.ArgumentParser(description="地理位置查询工具")
    # 必传参数
    parser.add_argument("--query", required=True, help="地址/地点查询关键词（必填）")
    # 可选参数，和函数默认值对齐
    parser.add_argument("--lng", type=float, default=None, help="经度")
    parser.add_argument("--lat", type=float, default=None, help="纬度")
    parser.add_argument("--radius", type=int, default=10000, help="搜索半径，默认10000米")
    parser.add_argument("--language", default="en", help="返回语言，默认en")

    # 2. 解析终端传入的参数
    args = parser.parse_args()

    # 3. 调用业务函数
    result = search_location(
        query=args.query,
        lng=args.lng,
        lat=args.lat,
        radius=args.radius,
        language=args.language
    )

    # 4. 打印输出结果（控制台展示）
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))