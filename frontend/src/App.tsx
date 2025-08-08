import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import Header from './components/common/Header'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import AdminPage from './pages/AdminPage'
import ChatlogImportPage from './pages/ChatlogImportPage'
import AIManagementPage from './pages/AIManagementPage'

const { Content, Footer } = Layout

const App: React.FC = () => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header />
      <Content style={{ padding: '24px', flex: 1 }}>
        <div className="container" style={{ maxWidth: 1200, margin: '0 auto' }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/import" element={<ChatlogImportPage />} />
            <Route path="/ai" element={<AIManagementPage />} />
          </Routes>
        </div>
      </Content>
      <Footer style={{ textAlign: 'center' }}>
        微信群问答知识库 ©2024 Created by ChatLog Team
      </Footer>
    </Layout>
  )
}

export default App