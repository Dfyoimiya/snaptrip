import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { message } from 'antd';
import { useNavigate } from '@umijs/max';
import { loginAPI } from '@/services/auth';
import { setToken, setRefreshToken } from '@/utils/auth';

export default function LoginPage() {
  const navigate = useNavigate();

  const handleSubmit = async (values: API.LoginRequest) => {
    try {
      const res = await loginAPI(values);
      setToken(res.data.accessToken);
      setRefreshToken(res.data.refreshToken);
      message.success('Login successful');
      navigate('/');
    } catch {
      // error handled by interceptor
    }
  };

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: '#f0f2f5',
      }}
    >
      <div style={{ width: 400 }}>
        <h1 style={{ textAlign: 'center', marginBottom: 24 }}>SnapTrip Admin</h1>
        <LoginForm onFinish={handleSubmit}>
          <ProFormText
            name="email"
            placeholder="Email"
            rules={[{ required: true, message: 'Please enter email' }]}
          />
          <ProFormText.Password
            name="password"
            placeholder="Password"
            rules={[{ required: true, message: 'Please enter password' }]}
          />
        </LoginForm>
      </div>
    </div>
  );
}
