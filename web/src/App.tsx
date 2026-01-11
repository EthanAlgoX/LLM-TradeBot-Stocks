import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Today from './pages/Today'
import Yesterday from './pages/Yesterday'
import Header from './components/layout/Header'

function App() {
    return (
        <BrowserRouter>
            <div className="min-h-screen bg-dark-300">
                <Header />
                <main className="container mx-auto px-4 py-8">
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/today" element={<Today />} />
                        <Route path="/yesterday" element={<Yesterday />} />
                    </Routes>
                </main>
            </div>
        </BrowserRouter>
    )
}

export default App
