# dy-tool-server

## 认证方式
### 1. JWT Token 认证 (推荐)
在请求头中添加:
```
Authorization: Bearer <your_jwt_token>
```

### 2. 跳过认证 Token (开发/测试用)
在请求头中添加:
```
skip-auth-token: <skip_auth_token_value>
```

## 使用说明
1. **JWT Token 获取**: 通过登录接口获取 JWT Token
2. **Skip Auth Token**: 仅用于开发和测试环境，生产环境请关闭此功能
3. **API 基础路径**: `/`
4. **响应格式**: 所有接口统一返回 JSON 格式

A RESTful API built with Flask.

## Installation
### 1. Using UV
1. Create a virtual environment
```bash
uv init --python 3.10 # create
uv venv --python 3.10 # if exists
```
2. Install dependencies
```bash
uv add -r requirements.txt # base
uv add -r requirements_mcp.txt # mcp support
```
3. Sync dependencies
```bash
uv sync 
```

### 2. Using PIP
1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Running the Application

```bash
python app.py
```

The API will be available at http://localhost:5000

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/users` - Get all users
- `POST /api/users` - Create a new user

## Example Usage

### Health Check
```bash
curl http://localhost:5000/api/health
```

### Get Users
```bash
curl http://localhost:5000/api/users
```

### Create User
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```