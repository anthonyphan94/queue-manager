import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Marketing from './views/Marketing';

function App(): JSX.Element {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/*" element={<Marketing />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
