import React from 'react';
import Sidebar from '@/components/layout/sidebar/Sidebar';
// import './DashboardLayout.css';
import clockIcon from '@/assets/icons/clock.svg';
import computerIcon from '@/assets/icons/computer-icon.svg';
import depositIcon from '@/assets/icons/deposit.svg';
import withdrawIcon from '@/assets/icons/withdraw.svg';

const dashboardItems = [
  {
    id: 'dashboard',
    name: 'Dashboard',
    link: '/dashboard',
    icon: computerIcon,
  },
  {
    id: 'position_history',
    name: 'Position History',
    link: '/dashboard/position-history',
    icon: clockIcon,
  },
  {
    id: 'deposit',
    name: 'Add Deposit',
    link: '/dashboard/deposit',
    icon: depositIcon,
  },
  {
    id: 'withdraw',
    name: 'Withdraw All',
    link: '/dashboard/withdraw',
    icon: withdrawIcon,
  },
];

export default function DashboardLayout({ children, title = 'zkLend Position' }) {
  return (
  <div className="min-h-screen flex w-screen lg:w-[calc(100vw-372px)] lg:ml-[372px] md:justify-center ">
      <Sidebar items={dashboardItems} />
      <div className="relative flex justify-center border border-solid  items-center w-full h-full">
        <div className="flex flex-col justify-center gap-2.5 p-6 pt-5 mt-24 mb-12 h-full w-full md:w-auto max-w-[400px] md:max-w-none">
          <h1 className="mt-4 text-2xl font-semibold text-second-primary text-center">{title}</h1>
        <div className="w-full gap-6  rounded-2xl  text-second-primary text-center flex justify-center flex-col ">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}