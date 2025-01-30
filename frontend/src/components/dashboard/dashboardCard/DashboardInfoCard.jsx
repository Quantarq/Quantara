import { useState } from "react";
import DashboardTabs from "@/components/dashboard/dashboard-tab/DashboardTabs"
import Collateral from "@/components/dashboard/collateral/Collateral"
import Borrow from "@/components/dashboard/borrow/Borrow"
import Deposited from "@/components/dashboard/deposited/Deposited"
import { DASHBOARD_TABS } from "@/utils/constants"


export default function DashboardInfoCard({ cardData, startSum, currentSum, depositedData }) {
    const [activeTab, setActiveTab] = useState(DASHBOARD_TABS.COLLATERAL)
    const { COLLATERAL, BORROW, DEPOSITED } = DASHBOARD_TABS
  
    const getCurrentSumColor = () => {
      if (currentSum > startSum) return "current-sum-green"
      if (currentSum < startSum) return "current-sum-red"
      return "" //string
    }
  
    return (
      <div className="dashboard-info-card">
        <DashboardTabs activeTab={activeTab} switchTab={setActiveTab} />
  
        {activeTab === COLLATERAL && (
          <Collateral
            getCurrentSumColor={getCurrentSumColor}
            startSum={startSum}
            currentSum={currentSum}
            data={cardData}
          />
        )}
  
        {activeTab === BORROW && <Borrow data={cardData} />}
  
        {activeTab === DEPOSITED && <Deposited data={depositedData} />}
      </div>
    )
  }