import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Dashboard from './views/Dashboard';

function App(): JSX.Element {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Dashboard />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
