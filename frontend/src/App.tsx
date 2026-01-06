import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './views/Dashboard';
import Marketing from './views/Marketing';

function App(): JSX.Element {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/marketing" element={<Marketing />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
