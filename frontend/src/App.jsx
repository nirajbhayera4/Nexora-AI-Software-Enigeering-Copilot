import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Home from './pages/Home';
import ConnectRepository from './pages/ConnectRepository';
import ThreeBackground from './components/ThreeBackground';

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <ThreeBackground />
      <Routes>
        <Route path="/" element={<div className="app-page"><Home /></div>} />
        <Route path="/connect" element={<div className="app-page"><ConnectRepository /></div>} />
      </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
