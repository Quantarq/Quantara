import { useState } from "react"
import HealthIcon from "@/assets/icons/health.svg?react"
import EthIcon from "@/assets/icons/ethereum.svg?react"
import Card from "@/components/ui/card/Card"
import { Button } from "@/components/ui/custom-button/Button"
import Spinner from "@/components/ui/spinner/Spinner"
import { useCheckPosition, useClosePosition } from "@/hooks/useClosePosition"
import useDashboardData from "@/hooks/useDashboardData"
import { useWalletStore } from "@/stores/useWalletStore"
import DashboardLayout from "../DashboardLayout"
import DashboardInfoCard from "@/components/dashboard/dashboardCard/DashboardInfoCard"
import TelegramNotification from "@/components/ui/telegram-notification/TelegramNotification"

export default function DashboardPage({ telegramId }) {
  const { walletId } = useWalletStore()

  const { 
    cardData, 
    healthFactor, 
    startSum, 
    currentSum, 
    depositedData, 
    isLoading } = useDashboardData()

  const { 
    mutate:
     closePositionEvent,
    isLoading: isClosing } = useClosePosition(walletId)

  const { 
    data: positionData } = useCheckPosition()

  const hasOpenedPosition = positionData?.has_opened_position


  return (
    <DashboardLayout>
      {isLoading && <Spinner loading={isLoading} />}
      <div className="top-cards-dashboard">
        <Card label="Health Factor" value={healthFactor} icon={<HealthIcon className="icon" />} />
        <Card label="Borrow Balance" cardData={cardData} icon={<EthIcon className="icon" />} />
      </div>
      <div className="dashboard-info-container">
        <DashboardInfoCard
          cardData={cardData}
          startSum={startSum}
          currentSum={currentSum}
          depositedData={depositedData}
        />

        <Button
          className="redeem-btn"
          variant="primary"
          size="lg"
          onClick={() => closePositionEvent()}
          disabled={isClosing || !hasOpenedPosition}
        >
          {isClosing ?
           "Closing..." : "Redeem"}
        </Button>
        <TelegramNotification telegramId={telegramId}/>
      </div>
    </DashboardLayout>
  )
}

