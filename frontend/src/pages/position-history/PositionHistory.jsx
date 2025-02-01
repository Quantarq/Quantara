import EthIcon from '@/assets/icons/ethereum.svg?react';
import filterIcon from '@/assets/icons/filter-horizontal.svg';
import HealthIcon from '@/assets/icons/health.svg?react';
import StrkIcon from '@/assets/icons/strk.svg?react';
import UsdIcon from '@/assets/icons/usd_coin.svg?react';
import Card from '@/components/ui/card/Card';
import Spinner from '@/components/ui/spinner/Spinner';
import useDashboardData from '@/hooks/useDashboardData';
import { usePositionHistoryTable } from '@/hooks/usePositionHistory';
import PositionHistoryModal from '@/pages/position-history/PositionHistoryModal';
import PositionPagination from '@/pages/position-history/PositionPagination';
import { useState } from 'react';
import DashboardLayout from '../DashboardLayout';

function PositionHistory() {
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const positionsOnPage = 10;

  const { data: tableData, isPending } = usePositionHistoryTable(currentPage, positionsOnPage);
  const { data: cardData } = useDashboardData();

  const tokenIconMap = {
    STRK: <StrkIcon className="w-6 h-6 p-1 rounded-full bg-[#201338]" />,
    USDC: <UsdIcon className="w-6 h-6 p-1 rounded-full bg-[#201338]" />,
    ETH: <EthIcon className="w-6 h-6 p-1 rounded-full bg-[#201338]" />,
  };

  const statusStyles = {
    opened: 'text-[#49ABD2]',
    closed: 'text-[#FF5C5C]',
    pending: 'text-[#FFB800]',
  };

  return (
    <DashboardLayout title="Position History">
      <div className="flex flex-col items-center justify-center gap-0.5 pt-6 rounded-lg text-primary text-center">
        <div className="flex flex-col md:flex-row gap-2 w-full">
          <Card
            label="Health Factor"
            value={cardData?.health_ratio || '0.00'}
            icon={<HealthIcon className="mr-[5px] w-4 h-4" />}
          />
          <Card
            label="Borrow Balance"
            cardData={cardData?.borrowed || '0.00'}
            icon={<EthIcon className="mr-[5px] w-4 h-4" />}
          />
        </div>
      </div>
      <div className="w-full max-w-[1300px] mx-auto ">
        <div className="text-sm text-white mb-4 pl-2">
          <p>Position History</p>
        </div>

        <div className="border w-full border-[#36294E] rounded-lg overflow-auto [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-track]:bg-[#12072180] [&::-webkit-scrollbar-thumb]:bg-[#36294E] [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-[#4b3b69]">
          {isPending ? (
            <div className="flex justify-center items-center">
              <Spinner loading={isPending} />
            </div>
          ) : (
            <table className="w-full border-separate border-spacing-0 px-4">
              <thead>
                <tr className="flex gap-2 md:gap-3 border-b border-[#36294E]  text-[#9CA3AF] items-center py-4 text-[clamp(0.5rem,2vw,1rem)] font-normal justify-between">
                  <th className=""></th>
                  <th className="">Token</th>
                  <th className="">Amount</th>
                  <th className="">Created At</th>
                  <th className="">Status</th>
                  <th className="">Start Price</th>
                  <th className="">Multiplier</th>
                  <th className="">Liquidated</th>
                  <th className="">Closed At</th>
                  <th>
                    <img src={filterIcon} alt="filter-icon" draggable="false" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {!tableData?.positions || tableData?.positions.length === 0 ? (
                  <tr>
                    <td colSpan="10" className="text-center py-4">
                      No opened positions
                    </td>
                  </tr>
                ) : (
                  tableData?.positions.map((data, index) => (
                    <tr key={data.id} className="even:bg-[rgba(18,7,33,0.5)]">
                      <td className="py-4 px-4 text-[#9CA3AF]">{index + 1}.</td>
                      <td className="py-4 px-4">
                        <div className="flex items-center justify-center gap-2">
                          {tokenIconMap[data.token_symbol]}
                          <span className="text-white">{data.token_symbol.toUpperCase()}</span>
                        </div>
                      </td>
                      <td className="py-4 px-4 text-white text-center">{data.amount}</td>
                      <td className="py-4 px-4 text-white text-center">{data.created_at}</td>
                      <td className={`py-4 px-4 text-center font-semibold ${statusStyles[data.status.toLowerCase()]}`}>
                        {data.status}
                      </td>
                      <td className="py-4 px-4 text-white text-center">{data.start_price}</td>
                      <td className="py-4 px-4 text-white text-center">{data.multiplier}</td>
                      <td className="py-4 px-4 text-white text-center">{data.is_liquidated}</td>
                      <td className="py-4 px-4 text-white text-center">{data.closed_at}</td>
                      <td className="py-4 px-4 text-center">
                        <button
                          className="text-white p-1 rounded hover:bg-white/10 transition-colors"
                          onClick={() => setSelectedPosition({ data, index })}
                        >
                          &#x22EE;
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <PositionPagination
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        isPending={isPending}
        tableData={tableData}
        positionsOnPage={positionsOnPage}
      />

      {selectedPosition && (
        <PositionHistoryModal
          position={selectedPosition.data}
          onClose={() => setSelectedPosition(null)}
          tokenIcon={tokenIconMap}
          statusStyles={statusStyles}
          index={selectedPosition.index + 1}
        />
      )}
    </DashboardLayout>
  );
}

export default PositionHistory;
