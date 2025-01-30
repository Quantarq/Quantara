import React from 'react';
import UsdIcon from '@/assets/icons/usd_coin.svg?react';
import StrkIcon from '@/assets/icons/strk.svg?react';
import EthIcon from '@/assets/icons/ethereum.svg?react';

const Leaderboard = () => {
  const stats = {
    usdcPosition: 48390048,
    ethPosition: 2930,
    strgPosition: 89002039,
  };

  const tokenIcon = {
    STRK: <StrkIcon className="token-icon" />,
    USDC: <UsdIcon className="token-icon" />,
    ETH: <EthIcon className="token-icon" />,
  };

  const leaderboardData = [
    { id: 1, name: 'Name', address: '0x2326cE85ff591f2aBC3f5c2559...', positions: 98 },
    { id: 2, name: 'Name', address: '0x5294cE85ff591f2aBC3f5c7893...', positions: 96 },
    { id: 3, name: 'Name', address: '0x7754cE85ff591f2aBC3f5c2893...', positions: 95 },
    { id: 4, name: 'Name', address: '0x9924cE85ff591f2aBC3f5c2893...', positions: 94 },
    { id: 5, name: 'Name', address: '0x1124cE85ff591f2aBC3f5c2893...', positions: 93 },
    { id: 6, name: 'Name', address: '0x1124cE85ff591f2aBC3f5c2893...', positions: 93 },
    { id: 7, name: 'Name', address: '0x1124cE85ff591f2aBC3f5c2893...', positions: 93 },
  ];

  return (
    <main className="min-h-screen bg-[url(/assets/background-form.png)] p-6 text-white">
      <div className="w-[764px] mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-center">zkLend Leaderboard</h1>
        </div>

        {/* Stats Cards */}
        <section className="grid grid-cols-3 gap-4 mb-8">
          <div className="border border-[#36294E] py-[16px] px-[24px] rounded-lg">
            <div className="p-4">
              <div className="flex gap-2 text-[14px] text-gray-400">
                <span>{tokenIcon.USDC}</span>USDC Position
              </div>
              <div className="text-[24px] font-bold text-center text-[#F0F0F0]">
                {stats.usdcPosition.toLocaleString()}
              </div>
            </div>
          </div>

          <div className="border border-[#36294E] py-[16px] px-[24px] rounded-lg">
            <div className="p-4">
              <div className="flex gap-2 text-[14px] text-gray-400">
                <span>{tokenIcon.ETH}</span>ETH Position
              </div>
              <div className="text-[24px] font-bold text-center text-[#F0F0F0]">
                {stats.ethPosition.toLocaleString()}
              </div>
            </div>
          </div>

          <div className="border border-[#36294E] py-[16px] px-[24px] rounded-lg">
            <div className="p-4">
              <div className="flex gap-2 text-[14px] text-gray-400">
                <span>{tokenIcon.STRK}</span>STRK Position
              </div>
              <div className="text-[24px] font-bold text-center text-[#F0F0F0]">
                {stats.strgPosition.toLocaleString()}
              </div>
            </div>
          </div>
        </section>

        {/* Leaderboard Table */}
        <section className="border-[#36294E]">
          <div className="mb-5">
            <h2 className="text-xl font-bold">Leaderboard</h2>
          </div>
          <div className="border border-[#36294E] p-[24px] rounded-lg">
            <table className="w-full">
              <thead>
                <tr className="flex flex-row items-center gap-[150px] text-gray-400 text-sm border-b border-[#36294E]">
                  <th className="text-left py-4 pl-5 text-[14px]">Name</th>
                  <th className="text-left py-4 pl-8 text-[14px]">Opened Positions</th>
                  <th className="text-left py-4 text-[14px]">Tokens</th>
                </tr>
              </thead>
              <tbody>
                {leaderboardData.map((item) => (
                  <tr key={item.id} className="flex flex-row items-center gap-[250px] text-[#83919F]">
                    <span className="flex flex-row justify-between items-center gap-10">
                      <tr className="flex flex-row gap-5 items-center">
                        <td className="text-[12px]">{item.id}.</td>
                        <tr className="flex flex-col">
                          <td className="text-[14px]">{item.name}</td>
                          <td className="text-[12px]">{item.address}</td>
                        </tr>
                      </tr>
                      <span>
                        <td className="py-4 text-[14px]">{item.positions}</td>
                      </span>
                    </span>
                    <tr className="flex flex-row justify-between items-center">
                      <span>
                        <td className="py-4">
                          <div className="flex">
                            {tokenIcon.ETH}
                            {tokenIcon.STRK}
                          </div>
                        </td>
                      </span>
                    </tr>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
};

export default Leaderboard;
