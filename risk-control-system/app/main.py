"""FastAPI 应用入口 — 电商风险控制系统
直接运行: python app/main.py
前端页面: http://localhost:8000
"""

import os
import sys

# 确保项目根目录在 sys.path 中（支持 python app/main.py 和 uvicorn app.main:app 两种方式）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse
from app.database import engine, Base
from app.routers import api

# 创建应用
app = FastAPI(title="电商风险控制系统", version="1.0.0")

# 注册 API 路由
app.include_router(api.router)

# 静态文件
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Jinja2 模板
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


def render(name: str, **context):
    """绕过 Jinja2 版本 bug 的模板渲染函数"""
    tpl = templates.env.get_template(name)
    return HTMLResponse(tpl.render(**context))


@app.get("/")
def index():
    return render("index.html", current_page="index")


@app.get("/check")
def page_check():
    return render("check.html", current_page="check")


@app.get("/rules")
def page_rules():
    return render("rules.html", current_page="rules")


@app.get("/cases")
def page_cases():
    return render("cases.html", current_page="cases")


@app.get("/cases/{case_id}")
def page_case_detail(case_id: int):
    return render("case_detail.html", current_page="cases", case_id=case_id)


@app.get("/blacklist")
def page_blacklist():
    return render("blacklist.html", current_page="blacklist")


@app.get("/profile")
def page_profile():
    return render("profile.html", current_page="profile")


@app.get("/dashboard")
def page_dashboard():
    return render("dashboard.html", current_page="dashboard")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
