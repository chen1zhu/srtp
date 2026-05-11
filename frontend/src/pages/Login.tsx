import React, { useContext, useState } from 'react';
import { Form, Input, Button, Card, Alert, Typography, Space } from 'antd';
import { LockOutlined, UserOutlined, CompassOutlined } from '@ant-design/icons';
import { AuthContext } from '../context/AuthContext';

const { Title, Text } = Typography;

const Login: React.FC = () => {
  const { login, register } = useContext(AuthContext);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm();

  const onFinish = async (values: any) => {
    setLoading(true);
    setError(null);
    try {
      if (mode === 'login') {
        await login(values.identifier, values.password);
      } else {
        await register(values.username, values.email, values.password, values.full_name);
      }
    } catch (e: any) {
      setError(e?.message || (mode === 'login' ? '登录失败' : '注册失败'));
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setError(null);
    setMode((current) => (current === 'login' ? 'register' : 'login'));
    form.resetFields();
  };

  return (
    <div
      className="app-gradient"
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        padding: 20,
      }}
    >
      <Card
        bordered={false}
        style={{
          width: 'min(460px, 100%)',
          boxShadow: '0 22px 60px rgba(15, 23, 42, 0.14)',
          borderRadius: 22,
          overflow: 'hidden',
          background: 'linear-gradient(155deg, rgba(255,255,255,0.95) 0%, rgba(247,250,253,0.92) 100%)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <div style={{ marginBottom: 20, textAlign: 'center' }}>
          <div
            style={{
              width: 56,
              height: 56,
              margin: '0 auto 12px',
              borderRadius: 16,
              display: 'grid',
              placeItems: 'center',
              background: 'linear-gradient(135deg, #1f6feb 0%, #0f766e 100%)',
              boxShadow: '0 12px 26px rgba(31,111,235,0.28)',
            }}
          >
            <CompassOutlined style={{ color: '#fff', fontSize: 26 }} />
          </div>
          <Title level={3} style={{ margin: 0, color: '#0f172a', fontFamily: 'Manrope, "Noto Sans SC", sans-serif', letterSpacing: '0.01em' }}>
            地理空间分析工作台
          </Title>
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            {mode === 'login' ? '登录后继续访问' : '创建账户后开始使用'}
          </Text>
        </div>

        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} />}

        <Form form={form} layout="vertical" onFinish={onFinish} size="large">
          {mode === 'register' && (
            <Form.Item name="full_name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
              <Input placeholder="请输入姓名" autoComplete="name" />
            </Form.Item>
          )}
          {mode === 'register' && (
            <Form.Item name="email" label="邮箱" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入有效邮箱地址' }]}>
              <Input placeholder="请输入邮箱" autoComplete="email" />
            </Form.Item>
          )}
          <Form.Item name={mode === 'login' ? 'identifier' : 'username'} label={mode === 'login' ? '用户名或邮箱' : '用户名'} rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder={mode === 'login' ? '请输入用户名或邮箱' : '请输入用户名'} autoComplete="username" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              ...(mode === 'register' ? [{ min: 8, message: '密码至少 8 位' }] : []),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" autoComplete="current-password" />
          </Form.Item>
          {mode === 'register' && (
            <Form.Item
              name="confirm_password"
              label="确认密码"
              dependencies={['password']}
              rules={[
                { required: true, message: '请再次输入密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'));
                  },
                }),
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="请再次输入密码" autoComplete="new-password" />
            </Form.Item>
          )}
          <Form.Item style={{ marginBottom: 4 }}>
            <Space direction="vertical" size={10} style={{ width: '100%' }}>
              <Button type="primary" htmlType="submit" loading={loading} block style={{ height: 44, borderRadius: 12 }}>
                {mode === 'login' ? '登录' : '注册并进入'}
              </Button>
              <Button type="link" onClick={switchMode} block style={{ paddingInline: 0, color: '#0f766e' }}>
                {mode === 'login' ? '没有账号，立即注册' : '已有账号，返回登录'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
