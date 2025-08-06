# Chatlog API Specification

## API Overview

**Base URL**: `http://localhost:5000/api/v1`
**Authentication**: None required for MVP
**Content-Type**: `application/json`
**Response Format**: JSON

## API Response Format

### Standard Response Structure
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-01-15T10:30:00Z",
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 100,
    "hasNext": true
  }
}
```

### Error Response Structure
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "输入数据验证失败",
    "details": {
      "field": "question",
      "reason": "不能为空"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## API Endpoints

### 1. File Upload Endpoints

#### POST /upload/file
上传微信群聊记录JSON文件

**Request**:
```http
POST /api/v1/upload/file
Content-Type: multipart/form-data

file: [JSON file]
```

**Response**:
```json
{
  "success": true,
  "data": {
    "uploadId": "upload_123456789",
    "filename": "wechat_group_20240115.json",
    "fileSize": 1024000,
    "status": "processing"
  },
  "message": "文件上传成功，正在处理中"
}
```

#### GET /upload/status/{uploadId}
查询文件处理状态

**Response**:
```json
{
  "success": true,
  "data": {
    "uploadId": "upload_123456789",
    "status": "completed",
    "progress": 100,
    "stats": {
      "totalMessages": 1500,
      "extractedQA": 245,
      "processingTime": 30.5
    },
    "error": null
  }
}
```

#### GET /upload/history
获取上传历史记录

**Query Parameters**:
- `page` (optional): 页码，默认1
- `size` (optional): 每页数量，默认20

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "filename": "wechat_group_20240115.json",
      "fileSize": 1024000,
      "totalMessages": 1500,
      "extractedQA": 245,
      "status": "completed",
      "uploadedAt": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 5,
    "hasNext": false
  }
}
```

### 2. QA Management Endpoints

#### GET /qa
获取问答列表

**Query Parameters**:
- `page` (optional): 页码，默认1
- `size` (optional): 每页数量，默认20
- `category` (optional): 分类ID筛选
- `advisor` (optional): 回答者筛选
- `startDate` (optional): 开始日期 (YYYY-MM-DD)
- `endDate` (optional): 结束日期 (YYYY-MM-DD)

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "question": "如何使用chatlog导出微信群记录？",
      "answer": "可以通过以下步骤导出：1. 打开微信群聊 2. 点击右上角设置...",
      "category": {
        "id": 1,
        "name": "使用教程",
        "color": "#52c41a"
      },
      "asker": "张三",
      "advisor": "李老师",
      "confidence": 0.85,
      "createdAt": "2024-01-15T10:30:00Z",
      "updatedAt": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 245,
    "hasNext": true
  }
}
```

#### GET /qa/{id}
获取问答详情

**Response**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "question": "如何使用chatlog导出微信群记录？",
    "answer": "可以通过以下步骤导出：1. 打开微信群聊 2. 点击右上角设置...",
    "category": {
      "id": 1,
      "name": "使用教程",
      "color": "#52c41a"
    },
    "asker": "张三",
    "advisor": "李老师",
    "confidence": 0.85,
    "sourceFile": "wechat_group_20240115.json",
    "originalContext": "上下文对话内容...",
    "createdAt": "2024-01-15T10:30:00Z",
    "updatedAt": "2024-01-15T10:30:00Z"
  }
}
```

#### PUT /qa/{id}
更新问答内容

**Request**:
```json
{
  "question": "更新后的问题",
  "answer": "更新后的答案",
  "categoryId": 2
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "question": "更新后的问题",
    "answer": "更新后的答案",
    "updatedAt": "2024-01-15T11:00:00Z"
  },
  "message": "问答更新成功"
}
```

#### DELETE /qa/{id}
删除问答

**Response**:
```json
{
  "success": true,
  "message": "问答删除成功"
}
```

### 3. Search Endpoints

#### GET /search
搜索问答

**Query Parameters**:
- `q` (required): 搜索关键词
- `page` (optional): 页码，默认1
- `size` (optional): 每页数量，默认20
- `category` (optional): 分类ID筛选
- `advisor` (optional): 回答者筛选
- `startDate` (optional): 开始日期
- `endDate` (optional): 结束日期

**Response**:
```json
{
  "success": true,
  "data": {
    "query": "导出微信",
    "results": [
      {
        "id": 1,
        "question": "如何使用chatlog<mark>导出微信</mark>群记录？",
        "answer": "可以通过以下步骤<mark>导出</mark>：1. 打开<mark>微信</mark>群聊...",
        "category": {
          "id": 1,
          "name": "使用教程",
          "color": "#52c41a"
        },
        "asker": "张三",
        "advisor": "李老师",
        "confidence": 0.95,
        "relevanceScore": 0.92,
        "createdAt": "2024-01-15T10:30:00Z"
      }
    ],
    "facets": {
      "categories": [
        { "name": "使用教程", "count": 15 },
        { "name": "技术支持", "count": 8 }
      ],
      "advisors": [
        { "name": "李老师", "count": 12 },
        { "name": "王老师", "count": 11 }
      ]
    }
  },
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 23,
    "hasNext": true
  }
}
```

#### GET /search/suggestions
获取搜索建议

**Query Parameters**:
- `q` (required): 部分搜索词

**Response**:
```json
{
  "success": true,
  "data": {
    "suggestions": [
      "导出微信群记录",
      "导出聊天记录",
      "微信群数据导出"
    ]
  }
}
```

#### GET /search/popular
获取热门搜索

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "query": "导出微信",
      "count": 156
    },
    {
      "query": "使用教程",
      "count": 98
    }
  ]
}
```

### 4. Category Management Endpoints

#### GET /categories
获取分类列表

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "产品咨询",
      "description": "关于产品功能和特性的问题",
      "color": "#1890ff",
      "qaCount": 45,
      "createdAt": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "name": "技术支持",
      "description": "技术问题和故障排除",
      "color": "#f5222d",
      "qaCount": 32,
      "createdAt": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### POST /categories
创建新分类

**Request**:
```json
{
  "name": "新分类名称",
  "description": "分类描述",
  "color": "#52c41a"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "id": 6,
    "name": "新分类名称",
    "description": "分类描述",
    "color": "#52c41a",
    "qaCount": 0,
    "createdAt": "2024-01-15T11:00:00Z"
  },
  "message": "分类创建成功"
}
```

#### PUT /categories/{id}
更新分类

**Request**:
```json
{
  "name": "更新后的分类名称",
  "description": "更新后的描述",
  "color": "#722ed1"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "更新后的分类名称",
    "description": "更新后的描述",
    "color": "#722ed1",
    "qaCount": 45,
    "updatedAt": "2024-01-15T11:00:00Z"
  },
  "message": "分类更新成功"
}
```

#### DELETE /categories/{id}
删除分类

**Response**:
```json
{
  "success": true,
  "message": "分类删除成功"
}
```

### 5. Admin & Statistics Endpoints

#### GET /admin/stats
获取系统统计信息

**Response**:
```json
{
  "success": true,
  "data": {
    "overview": {
      "totalQA": 245,
      "totalCategories": 5,
      "totalUploads": 8,
      "avgConfidence": 0.83
    },
    "trends": {
      "qaByMonth": [
        { "month": "2024-01", "count": 156 },
        { "month": "2024-02", "count": 89 }
      ],
      "topCategories": [
        { "name": "产品咨询", "count": 78 },
        { "name": "技术支持", "count": 56 }
      ],
      "topAdvisors": [
        { "name": "李老师", "count": 89 },
        { "name": "王老师", "count": 67 }
      ]
    },
    "quality": {
      "highConfidence": 156,
      "mediumConfidence": 67,
      "lowConfidence": 22
    }
  }
}
```

#### POST /admin/reindex
重建搜索索引

**Response**:
```json
{
  "success": true,
  "data": {
    "indexedRecords": 245,
    "processingTime": 15.6
  },
  "message": "搜索索引重建完成"
}
```

#### GET /admin/health
系统健康检查

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "database": {
      "connected": true,
      "size": "15.6MB"
    },
    "storage": {
      "used": "234MB",
      "available": "1.2GB"
    },
    "memory": {
      "used": "128MB",
      "total": "512MB"
    }
  }
}
```

## Data Models

### QAPair Model
```typescript
interface QAPair {
  id: number;
  question: string;
  answer: string;
  category: Category;
  asker?: string;
  advisor?: string;
  confidence: number;        // 0.0 - 1.0
  sourceFile?: string;
  originalContext?: string;
  createdAt: Date;
  updatedAt: Date;
}
```

### Category Model
```typescript
interface Category {
  id: number;
  name: string;
  description?: string;
  color: string;            // Hex color code
  qaCount: number;
  createdAt: Date;
}
```

### Upload Model
```typescript
interface UploadRecord {
  id: number;
  filename: string;
  fileSize: number;
  totalMessages: number;
  extractedQA: number;
  status: 'processing' | 'completed' | 'error';
  errorMessage?: string;
  uploadedAt: Date;
}
```

### SearchResult Model
```typescript
interface SearchResult {
  qa: QAPair;
  relevanceScore: number;   // 0.0 - 1.0
  highlights: {
    question?: string;
    answer?: string;
  };
}
```

## Error Codes

### HTTP Status Codes
- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `422 Unprocessable Entity`: 数据验证失败
- `500 Internal Server Error`: 服务器内部错误

### Custom Error Codes
```typescript
enum ErrorCode {
  // Validation errors
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  REQUIRED_FIELD_MISSING = 'REQUIRED_FIELD_MISSING',
  INVALID_FORMAT = 'INVALID_FORMAT',
  
  // Upload errors
  FILE_TOO_LARGE = 'FILE_TOO_LARGE',
  INVALID_FILE_TYPE = 'INVALID_FILE_TYPE',
  UPLOAD_PROCESSING_ERROR = 'UPLOAD_PROCESSING_ERROR',
  
  // Search errors
  SEARCH_INDEX_ERROR = 'SEARCH_INDEX_ERROR',
  INVALID_SEARCH_QUERY = 'INVALID_SEARCH_QUERY',
  
  // Database errors
  DATABASE_CONNECTION_ERROR = 'DATABASE_CONNECTION_ERROR',
  RECORD_NOT_FOUND = 'RECORD_NOT_FOUND',
  DUPLICATE_RECORD = 'DUPLICATE_RECORD',
  
  // System errors
  INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'
}
```

## Rate Limiting

### Rate Limits (per IP)
- **Search**: 60 requests/minute
- **Upload**: 5 requests/minute
- **Admin**: 30 requests/minute
- **General**: 100 requests/minute

### Rate Limit Headers
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 58
X-RateLimit-Reset: 1642248600
```

## API Versioning

### Version Strategy
- **Current Version**: v1
- **URL Pattern**: `/api/v1/*`
- **Version Header**: `Accept: application/json; version=1`

### Backward Compatibility
- Minor version updates: backward compatible
- Major version updates: maintain previous version for 6 months

## Security Considerations

### Input Validation
```python
# Request validation schemas
upload_schema = {
    "type": "object",
    "properties": {
        "file": {
            "type": "file",
            "maxSize": 52428800,  # 50MB
            "allowedTypes": ["application/json"]
        }
    },
    "required": ["file"]
}

qa_update_schema = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "maxLength": 1000},
        "answer": {"type": "string", "maxLength": 5000},
        "categoryId": {"type": "integer", "minimum": 1}
    }
}
```

### Data Sanitization
- HTML entities encoding
- SQL injection prevention
- XSS attack prevention
- File content validation

## Performance Considerations

### Caching Strategy
- **Search Results**: Cache for 5 minutes
- **Categories**: Cache for 30 minutes
- **Statistics**: Cache for 1 hour

### Database Optimization
- Full-text search indexing
- Query result pagination
- Database connection pooling
- Prepared statements

### Response Optimization
- GZIP compression
- JSON response minification
- Conditional requests (ETag)
- Partial content support