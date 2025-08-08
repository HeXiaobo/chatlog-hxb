import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Tabs, 
  Statistic, 
  Progress, 
  Alert, 
  Button, 
  Switch,
  Table,
  message,
  Spin,
  Tag,
  Typography,
  Space,
  Modal,
  Form,
  InputNumber,
  Tooltip,
  Input,
  Select,
  Popconfirm
} from 'antd';
import {
  DashboardOutlined,
  SettingOutlined,
  BarChartOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  ExportOutlined,
  PlusOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import { aiService } from '../services/aiService';
import type { AIStatus, AIUsageReport, AIConfig } from '../types/ai';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

const AIManagementPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [aiConfig, setAiConfig] = useState<AIConfig | null>(null);
  const [usageReport, setUsageReport] = useState<AIUsageReport | null>(null);
  const [configModalVisible, setConfigModalVisible] = useState(false);
  const [addProviderModalVisible, setAddProviderModalVisible] = useState(false);
  const [testingProvider, setTestingProvider] = useState<string>('');
  const [form] = Form.useForm();
  const [addForm] = Form.useForm();

  // AI提供商配置模板
  const providerTemplates: Record<string, any> = {
    'kimi': {
      model_name: 'moonshot-v1-8k',
      api_base: 'https://api.moonshot.cn/v1/',
      max_tokens: 8000,
      cost_per_1k_tokens: 0.012,
      daily_limit: 5000,
      description: '月之暗面Kimi，擅长长文本理解和生成'
    },
    'doubao': {
      model_name: 'ep-20240611073937-h8l9s',
      api_base: 'https://ark.cn-beijing.volces.com/api/v3/',
      max_tokens: 4000,
      cost_per_1k_tokens: 0.0008,
      daily_limit: 15000,
      description: '字节豆包大模型，高性价比选择'
    },
    'deepseek': {
      model_name: 'deepseek-chat',
      api_base: 'https://api.deepseek.com/v1/',
      max_tokens: 4000,
      cost_per_1k_tokens: 0.00014,
      daily_limit: 50000,
      description: 'DeepSeek大模型，极具竞争力的定价'
    },
    'zhipu': {
      model_name: 'glm-4',
      api_base: 'https://open.bigmodel.cn/api/paas/v4/',
      max_tokens: 4000,
      cost_per_1k_tokens: 0.001,
      daily_limit: 15000,
      description: '智谱AI GLM系列，中文理解能力强'
    },
    'baidu': {
      model_name: 'ernie-bot-turbo',
      api_base: 'https://aip.baidubce.com/',
      max_tokens: 2000,
      cost_per_1k_tokens: 0.0008,
      daily_limit: 20000,
      description: '百度文心一言，成熟的中文大模型'
    },
    'openai': {
      model_name: 'gpt-3.5-turbo',
      api_base: 'https://api.openai.com/v1/',
      max_tokens: 4000,
      cost_per_1k_tokens: 0.002,
      daily_limit: 10000,
      description: 'OpenAI GPT系列，业界标杆'
    },
    'anthropic': {
      model_name: 'claude-3-sonnet-20240229',
      api_base: 'https://api.anthropic.com/',
      max_tokens: 4000,
      cost_per_1k_tokens: 0.003,
      daily_limit: 8000,
      description: 'Anthropic Claude系列，安全可靠'
    },
    'ollama': {
      model_name: 'llama2:7b',
      api_base: 'http://localhost:11434/',
      max_tokens: 2000,
      cost_per_1k_tokens: 0,
      daily_limit: 50000,
      description: 'Ollama本地模型，完全免费'
    }
  };

  useEffect(() => {
    loadInitialData();
    // 设置定时刷新
    const interval = setInterval(loadAIStatus, 30000); // 30秒刷新一次
    return () => clearInterval(interval);
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadAIStatus(),
        loadAIConfig(),
        loadUsageReport()
      ]);
    } catch (error) {
      message.error('加载AI管理数据失败');
    } finally {
      setLoading(false);
    }
  };

  const loadAIStatus = async () => {
    try {
      const status = await aiService.getAIStatus();
      setAiStatus(status);
    } catch (error) {
      console.error('Failed to load AI status:', error);
    }
  };

  const loadAIConfig = async () => {
    try {
      const config = await aiService.getAIConfig();
      setAiConfig(config);
    } catch (error) {
      console.error('Failed to load AI config:', error);
    }
  };

  const loadUsageReport = async () => {
    try {
      const report = await aiService.getUsageReport('24h');
      setUsageReport(report);
    } catch (error) {
      console.error('Failed to load usage report:', error);
    }
  };

  const testProviderConnection = async (provider: string) => {
    setTestingProvider(provider);
    try {
      const result = await aiService.testProviderConnection(provider);
      if (result.success) {
        message.success(`${provider} 连接测试成功`);
      } else {
        message.error(`${provider} 连接测试失败: ${result.error}`);
      }
    } catch (error) {
      message.error(`连接测试失败: ${error}`);
    } finally {
      setTestingProvider('');
    }
  };

  const updateProviderConfig = async (provider: string, values: any) => {
    try {
      await aiService.updateAIConfig(provider, values);
      message.success('配置更新成功');
      await loadAIConfig();
    } catch (error) {
      message.error('配置更新失败');
    }
  };

  const resetDailyStats = async () => {
    try {
      await aiService.resetDailyStats();
      message.success('每日统计重置成功');
      await loadAIStatus();
    } catch (error) {
      message.error('重置失败');
    }
  };

  const addNewProvider = async (values: any) => {
    try {
      await aiService.addAIProvider(values);
      message.success(`AI提供商 ${values.provider} 添加成功`);
      setAddProviderModalVisible(false);
      addForm.resetFields();
      await loadAIConfig();
    } catch (error: any) {
      const errorMsg = error.response?.data?.error?.message || '添加提供商失败';
      message.error(errorMsg);
    }
  };

  const removeProvider = async (provider: string) => {
    try {
      await aiService.removeAIProvider(provider);
      message.success(`AI提供商 ${provider} 删除成功`);
      await loadAIConfig();
    } catch (error: any) {
      const errorMsg = error.response?.data?.error?.message || '删除提供商失败';
      message.error(errorMsg);
    }
  };

  const handleProviderChange = (provider: string) => {
    const template = providerTemplates[provider];
    if (template) {
      addForm.setFieldsValue({
        provider,
        model_name: template.model_name,
        api_base: template.api_base,
        max_tokens: template.max_tokens,
        cost_per_1k_tokens: template.cost_per_1k_tokens,
        daily_limit: template.daily_limit
      });
    }
  };

  const exportReport = async (period: string) => {
    try {
      const exportData = await aiService.exportUsageReport(period);
      // 创建下载链接
      const blob = new Blob([exportData.content], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ai_usage_report_${period}.json`;
      a.click();
      window.URL.revokeObjectURL(url);
      message.success('报告导出成功');
    } catch (error) {
      message.error('导出失败');
    }
  };

  const getHealthStatusColor = (level: string) => {
    switch (level) {
      case 'excellent': return 'success';
      case 'good': return 'processing';
      case 'fair': return 'warning';
      case 'poor': return 'error';
      default: return 'default';
    }
  };

  const getHealthStatusText = (level: string) => {
    switch (level) {
      case 'excellent': return '优秀';
      case 'good': return '良好';
      case 'fair': return '一般';
      case 'poor': return '较差';
      default: return '未知';
    }
  };

  const renderOverviewTab = () => (
    <div>
      {/* 系统健康状态 */}
      <Card title="系统健康状态" style={{ marginBottom: 16 }}>
        {aiStatus?.system_health ? (
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="健康评分"
                value={aiStatus.system_health.health_score}
                suffix="/ 100"
                valueStyle={{ 
                  color: aiStatus.system_health.health_score >= 80 ? '#3f8600' : 
                         aiStatus.system_health.health_score >= 60 ? '#faad14' : '#cf1322'
                }}
              />
            </Col>
            <Col span={6}>
              <div>
                <Text strong>健康等级</Text>
                <br />
                <Tag color={getHealthStatusColor(aiStatus.system_health.health_level)}>
                  {getHealthStatusText(aiStatus.system_health.health_level)}
                </Tag>
              </div>
            </Col>
            <Col span={12}>
              <div>
                <Text strong>问题与建议</Text>
                <div style={{ marginTop: 8 }}>
                  {aiStatus.system_health.issues?.length > 0 ? (
                    aiStatus.system_health.issues.map((issue, index) => (
                      <Alert key={index} message={issue} type="warning" showIcon style={{ marginBottom: 4 }} />
                    ))
                  ) : (
                    <Alert message="系统运行正常" type="success" showIcon />
                  )}
                </div>
              </div>
            </Col>
          </Row>
        ) : (
          <Alert message="无法获取健康状态" type="error" />
        )}
      </Card>

      {/* AI配置状态 */}
      <Card title="AI配置状态" style={{ marginBottom: 16 }}>
        {aiStatus?.config_status ? (
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="已配置提供商"
                value={aiStatus.config_status.total_providers}
                prefix={<CheckCircleOutlined />}
              />
            </Col>
            <Col span={6}>
              <div>
                <Text strong>主要提供商</Text>
                <br />
                <Tag color="blue">{aiStatus.config_status.primary_provider || '未配置'}</Tag>
              </div>
            </Col>
            <Col span={12}>
              <div>
                <Text strong>提供商状态</Text>
                <div style={{ marginTop: 8 }}>
                  {Object.entries(aiStatus.config_status.providers || {}).map(([provider, info]: [string, any]) => (
                    <div key={provider} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <Tag color={info.enabled ? 'green' : 'red'}>{provider}</Tag>
                      <Text>{info.remaining}/{info.daily_limit} 剩余</Text>
                    </div>
                  ))}
                </div>
              </div>
            </Col>
          </Row>
        ) : (
          <Alert message="无法获取配置状态" type="error" />
        )}
      </Card>

      {/* 使用统计 */}
      <Card title="今日使用统计" extra={
        <Button icon={<ReloadOutlined />} onClick={resetDailyStats}>
          重置统计
        </Button>
      }>
        {aiStatus?.usage_stats ? (
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="总请求数"
                value={aiStatus.usage_stats.total_requests}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="总消耗Token"
                value={aiStatus.usage_stats.total_tokens}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="总成本"
                value={aiStatus.usage_stats.total_cost}
                precision={4}
                prefix="$"
              />
            </Col>
            <Col span={6}>
              <div>
                <Text strong>提供商使用分布</Text>
                <div style={{ marginTop: 8 }}>
                  {Object.entries(aiStatus.usage_stats.providers || {}).map(([provider, stats]: [string, any]) => (
                    <div key={provider}>
                      <Text>{provider}: {stats.requests} 次</Text>
                      <Progress 
                        percent={Math.round((stats.requests / aiStatus.usage_stats.total_requests) * 100)} 
                        size="small" 
                        style={{ marginBottom: 4 }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </Col>
          </Row>
        ) : (
          <Alert message="暂无使用数据" type="info" />
        )}
      </Card>
    </div>
  );

  const renderConfigTab = () => (
    <div>
      {aiConfig ? (
        <Card 
          title="AI提供商配置"
          extra={
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={() => setAddProviderModalVisible(true)}
            >
              添加新提供商
            </Button>
          }
        >
          <Table
            dataSource={aiConfig.providers}
            columns={[
              {
                title: '提供商',
                dataIndex: 'provider',
                key: 'provider',
                render: (provider: string) => <Tag color="blue">{provider}</Tag>
              },
              {
                title: '模型',
                dataIndex: 'model_name',
                key: 'model_name'
              },
              {
                title: '状态',
                dataIndex: 'enabled',
                key: 'enabled',
                render: (enabled: boolean, record: any) => (
                  <Switch 
                    checked={enabled}
                    onChange={(checked) => updateProviderConfig(record.provider, { enabled: checked })}
                  />
                )
              },
              {
                title: '每日限制',
                dataIndex: 'daily_limit',
                key: 'daily_limit',
                render: (limit: number) => limit.toLocaleString()
              },
              {
                title: '已使用',
                dataIndex: ['usage_stats', 'daily_requests'],
                key: 'daily_used',
                render: (used: number, record: any) => (
                  <div>
                    <Text>{used.toLocaleString()}</Text>
                    <Progress 
                      percent={Math.round((used / record.daily_limit) * 100)}
                      size="small"
                      status={used / record.daily_limit > 0.8 ? 'exception' : 'active'}
                      style={{ marginTop: 4, width: 100 }}
                    />
                  </div>
                )
              },
              {
                title: '成功率',
                dataIndex: ['usage_stats', 'success_rate'],
                key: 'success_rate',
                render: (rate: number) => (
                  <Tag color={rate >= 95 ? 'green' : rate >= 80 ? 'orange' : 'red'}>
                    {rate.toFixed(1)}%
                  </Tag>
                )
              },
              {
                title: '操作',
                key: 'actions',
                render: (record: any) => (
                  <Space>
                    <Button 
                      size="small"
                      loading={testingProvider === record.provider}
                      onClick={() => testProviderConnection(record.provider)}
                    >
                      测试连接
                    </Button>
                    <Button size="small" onClick={() => {
                      form.setFieldsValue(record);
                      setConfigModalVisible(true);
                    }}>
                      配置
                    </Button>
                    <Popconfirm
                      title="确定要删除这个AI提供商吗？"
                      description="删除后将无法恢复，相关的使用统计也会被清除。"
                      onConfirm={() => removeProvider(record.provider)}
                      okText="删除"
                      cancelText="取消"
                      okType="danger"
                    >
                      <Button 
                        size="small" 
                        danger
                        icon={<DeleteOutlined />}
                      >
                        删除
                      </Button>
                    </Popconfirm>
                  </Space>
                )
              }
            ]}
            pagination={false}
            rowKey="provider"
          />
        </Card>
      ) : (
        <Alert message="无法加载配置数据" type="error" />
      )}

      <Modal
        title="配置AI提供商"
        open={configModalVisible}
        onOk={() => form.submit()}
        onCancel={() => setConfigModalVisible(false)}
        width={600}
      >
        <Form
          form={form}
          onFinish={(values) => {
            updateProviderConfig(values.provider, values);
            setConfigModalVisible(false);
          }}
          layout="vertical"
        >
          <Form.Item name="provider" label="提供商" style={{ display: 'none' }}>
            <input type="hidden" />
          </Form.Item>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item 
                name="max_tokens" 
                label="最大Token数"
                tooltip="单次请求的最大Token限制"
              >
                <InputNumber min={100} max={32000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item 
                name="temperature" 
                label="温度参数"
                tooltip="控制回答的随机性，0-1之间"
              >
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item 
                name="daily_limit" 
                label="每日请求限制"
                tooltip="每日最大请求次数"
              >
                <InputNumber min={100} max={100000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item 
                name="cost_per_1k_tokens" 
                label="千Token成本($)"
                tooltip="每1000个Token的成本"
              >
                <InputNumber min={0} max={1} step={0.0001} precision={4} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        title="添加新的AI提供商"
        open={addProviderModalVisible}
        onOk={() => addForm.submit()}
        onCancel={() => {
          setAddProviderModalVisible(false);
          addForm.resetFields();
        }}
        width={700}
      >
        <Form
          form={addForm}
          onFinish={addNewProvider}
          layout="vertical"
          initialValues={{
            max_tokens: 2000,
            temperature: 0.7,
            timeout: 60,
            enabled: true,
            cost_per_1k_tokens: 0.002,
            daily_limit: 10000
          }}
        >
          <Alert 
            message="添加新的AI提供商" 
            description="请填写完整的API信息。API Key等敏感信息会被安全存储。" 
            type="info" 
            showIcon 
            style={{ marginBottom: 16 }}
          />

          {/* 动态显示提供商信息 */}
          <Form.Item shouldUpdate={(prevValues, currentValues) => prevValues.provider !== currentValues.provider}>
            {({ getFieldValue }) => {
              const selectedProvider = getFieldValue('provider');
              const template = providerTemplates[selectedProvider];
              
              if (template) {
                return (
                  <Alert
                    message={`${selectedProvider.toUpperCase()} 配置信息`}
                    description={template.description}
                    type="success"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                );
              }
              return null;
            }}
          </Form.Item>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item 
                name="provider" 
                label="提供商名称"
                rules={[{ required: true, message: '请输入提供商名称' }]}
                tooltip="选择AI提供商，系统会自动填充推荐配置"
              >
                <Select
                  placeholder="选择AI提供商"
                  allowClear
                  showSearch
                  onChange={handleProviderChange}
                  options={[
                    { value: 'kimi', label: '🌙 月之暗面 Kimi' },
                    { value: 'doubao', label: '🫘 字节豆包' },
                    { value: 'deepseek', label: '🔍 DeepSeek' },
                    { value: 'zhipu', label: '🧠 智谱AI' },
                    { value: 'baidu', label: '🐻 百度文心一言' },
                    { value: 'alibaba', label: '☁️ 阿里云通义千问' },
                    { value: 'openai', label: '🤖 OpenAI' },
                    { value: 'anthropic', label: '🎭 Anthropic' },
                    { value: 'ollama', label: '🏠 Ollama本地' }
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item 
                name="model_name" 
                label="模型名称"
                rules={[{ required: true, message: '请输入模型名称' }]}
                tooltip="例如：gpt-3.5-turbo, claude-3-sonnet等"
              >
                <Input placeholder="输入具体的模型名称" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item 
                name="api_key" 
                label="API Key"
                rules={[{ required: true, message: '请输入API Key' }]}
                tooltip="从AI提供商获取的API密钥"
              >
                <Input.Password placeholder="输入API Key" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item 
                name="api_base" 
                label="API Base URL"
                tooltip="API的基础URL，如果使用官方API可以留空"
              >
                <Input placeholder="例如：https://api.openai.com/v1" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item 
                name="max_tokens" 
                label="最大Token数"
                tooltip="单次请求的最大Token限制"
              >
                <InputNumber min={100} max={32000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item 
                name="temperature" 
                label="温度参数"
                tooltip="控制回答的随机性，0-1之间"
              >
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item 
                name="timeout" 
                label="超时时间(秒)"
                tooltip="API请求超时时间"
              >
                <InputNumber min={10} max={300} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item 
                name="daily_limit" 
                label="每日请求限制"
                tooltip="每日最大请求次数"
              >
                <InputNumber min={100} max={100000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item 
                name="cost_per_1k_tokens" 
                label="千Token成本($)"
                tooltip="每1000个Token的成本"
              >
                <InputNumber min={0} max={1} step={0.0001} precision={4} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item 
                name="enabled" 
                label="启用状态"
                valuePropName="checked"
                tooltip="是否立即启用此提供商"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );

  const renderAnalyticsTab = () => (
    <div>
      {usageReport ? (
        <>
          <Card 
            title="使用报告 (最近24小时)" 
            extra={
              <Space>
                <Button icon={<ExportOutlined />} onClick={() => exportReport('24h')}>
                  导出报告
                </Button>
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            <Row gutter={16}>
              <Col span={8}>
                <Card size="small" title="提取性能">
                  <Statistic title="成功率" value={usageReport.extraction_metrics.success_rate * 100} precision={1} suffix="%" />
                  <Statistic title="平均置信度" value={usageReport.extraction_metrics.avg_confidence} precision={2} />
                  <Statistic title="平均处理时间" value={usageReport.extraction_metrics.avg_processing_time} precision={1} suffix="秒" />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" title="分类性能">
                  <Statistic title="分类准确率" value={usageReport.classification_metrics.success_rate * 100} precision={1} suffix="%" />
                  <Statistic title="平均置信度" value={usageReport.classification_metrics.avg_confidence} precision={2} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" title="成本分析">
                  <Statistic title="今日成本" value={usageReport.cost_analysis.daily_cost} precision={4} prefix="$" />
                  <Statistic title="预估月成本" value={usageReport.cost_analysis.estimated_monthly_cost} precision={2} prefix="$" />
                </Card>
              </Col>
            </Row>
          </Card>

          {/* 优化建议 */}
          <Card title="优化建议">
            {usageReport.recommendations.map((recommendation, index) => (
              <Alert
                key={index}
                message={recommendation}
                type="info"
                showIcon
                style={{ marginBottom: 8 }}
              />
            ))}
          </Card>
        </>
      ) : (
        <Alert message="无法加载分析数据" type="error" />
      )}
    </div>
  );

  if (loading) {
    return <Spin size="large" style={{ display: 'block', textAlign: 'center', marginTop: 100 }} />;
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <DashboardOutlined /> AI管理中心
      </Title>
      <Paragraph>
        管理和监控AI大模型的配置、使用情况和性能指标
      </Paragraph>

      <Tabs defaultActiveKey="overview" style={{ marginTop: 24 }}>
        <TabPane 
          tab={<span><DashboardOutlined />概览</span>} 
          key="overview"
        >
          {renderOverviewTab()}
        </TabPane>
        
        <TabPane 
          tab={<span><SettingOutlined />配置</span>} 
          key="config"
        >
          {renderConfigTab()}
        </TabPane>
        
        <TabPane 
          tab={<span><BarChartOutlined />分析</span>} 
          key="analytics"
        >
          {renderAnalyticsTab()}
        </TabPane>
      </Tabs>
    </div>
  );
};

export default AIManagementPage;