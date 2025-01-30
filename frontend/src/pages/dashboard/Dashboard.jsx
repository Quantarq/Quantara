import { useState } from "react"
import HealthIcon from "@/assets/icons/health.svg?react"
import EthIcon from "@/assets/icons/ethereum.svg?react"
import TelegramIcon from "@/assets/icons/telegram_dashboard.svg?react"
import { ActionModal } from "@/components/ui/action-modal"
import Card from "@/components/ui/card/Card"
import { Button } from "@/components/ui/custom-button/Button"
import Spinner from "@/components/ui/spinner/Spinner"
import { useCheckPosition, useClosePosition } from "@/hooks/useClosePosition"
import useDashboardData from "@/hooks/useDashboardData"
import useTelegramNotification from "@/hooks/useTelegramNotification"
import { useWalletStore } from "@/stores/useWalletStore"
import DashboardLayout from "../DashboardLayout"
import DashboardInfoCard from "@/components/dashboard/dashboardCard/DashboardInfoCard"

export default function DashboardPage({ telegramId }) {
  const { walletId } = useWalletStore()
  const [showModal, setShowModal] = useState(false)
  const handleOpen = () => setShowModal(true)
  const handleClose = () => setShowModal(false)

  const { 
    cardData, 
    healthFactor, 
    startSum, 
    currentSum, 
    depositedData, 
    isLoading } = useDashboardData()
  const { mutate: closePositionEvent, isLoading: isClosing } = useClosePosition(walletId)
  const { data: positionData } = useCheckPosition()
  const { subscribe } = useTelegramNotification()

  const hasOpenedPosition = positionData?.has_opened_position

  const handleSubscribe = () => subscribe({ telegramId, walletId })

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
          {isClosing ? "Closing..." : "Redeem"}
        </Button>
        <Button variant="secondary" size="lg" className="dashboard-btn telegram" onClick={handleOpen}>
          <TelegramIcon className="tab-icon" />
          Enable telegram notification bot
        </Button>
        {showModal && (
          <ActionModal
            isOpen={showModal}
            title="Telegram Notification"
            subTitle="Do you want to enable telegram notification bot?"
            content={[
              "This will allow you to receive quick notifications on your telegram line in realtime. You can disable this setting anytime.",
            ]}
            cancelLabel="Cancel"
            submitLabel="Yes, Sure"
            submitAction={handleSubscribe}
            cancelAction={handleClose}
          />
        )}
      </div>
    </DashboardLayout>
  )
}

