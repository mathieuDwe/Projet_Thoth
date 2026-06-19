import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import StatusBar from './StatusBar';

export default function AppLayout() {
  return (
    <div className="flex h-screen bg-gray-950">
      <Sidebar />

      <div className="flex-1 flex flex-col ml-64">
        <StatusBar />

        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
