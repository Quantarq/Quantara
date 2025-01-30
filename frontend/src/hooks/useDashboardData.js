import { useQuery } from "@tanstack/react-query"
import { useState, useEffect } from "react"
import QueryKeys from "../QueryKeys/QueryKeys"
import { axiosInstance } from "../utils/axios"
import { useWalletStore } from "../stores/useWalletStore"
import EthIcon from "@/assets/icons/ethereum.svg?react"
import StrkIcon from "@/assets/icons/strk.svg?react"
import UsdIcon from "@/assets/icons/usd_coin.svg?react"
import CollateralIcon from "@/assets/icons/collateral_dynamic.svg?react"
import BorrowIcon from "@/assets/icons/borrow_dynamic.svg?react"

export const fetchDashboardData = async (walletId) => {
  if (!walletId) {
    throw new Error('Wallet ID is undefined');
  }
  const response = await axiosInstance.get(`/api/dashboard?wallet_id=${walletId}`);
  return response.data;
};

const useDashboardData = () => {
  const walletId = useWalletStore((state) => state.walletId);
  const [cardData, setCardata]=useState([])
  const [healthFactor, setHealthFactor]=useState("0.00")
  const [startSum, setStartSum] = useState(0)
  const [currentSum, setCurrentSum] = useState(0)
  const [depositedData, setDepositedData] = useState({ eth: 0, strk: 0, usdc: 0, usdt: 0 })

  const {data, isLoading, error}= useQuery({
    queryKey: [QueryKeys.DashboardData, walletId],
    queryFn: () => fetchDashboardData(walletId),
    enabled: !!walletId,
    onError: (error) => {
      console.error("Error during getting the data from API", error)
    },
  })

useEffect(()=>{
  if(!isLoading && data){
    const{
      health_ratio,
      current_sum, 
      start_sum, 
      borrowed,
      multipliers,
      balance,
      deposit_data}=data

      // Update deposited data
      const updatedDepositedData = { eth: 0, strk: 0, usdc: 0, usdt: 0 }
      deposit_data.forEach((deposit) => {
      updatedDepositedData[deposit.token.toLowerCase()] += Number(deposit.amount)
      })

      // Determine currency name and icon
      
      let currencyName = "Ethereum"
      let currencyIcon = EthIcon
      if (multipliers) {
        if (multipliers.STRK) {
          currencyName = "STRK"
          currencyIcon = StrkIcon
        } else if (multipliers.ETH) {
          currencyName = "Ethereum"
          currencyIcon = EthIcon
        } else if (multipliers.USDC) {
          currencyName = "USDC"
          currencyIcon = UsdIcon
        }
      }


       // Update card data
       const updatedCardData = [
        {
          title: "Collateral & Earnings",
          icon: CollateralIcon,
          balance: balance,
          currencyName: currencyName,
          currencyIcon: currencyIcon,
        },
        {
          title: "Borrow",
          icon: BorrowIcon,
          balance: borrowed,
          currencyName: "USD Coin",
          currencyIcon: UsdIcon,
        },
      ]

      setCardata(updatedCardData)
      setHealthFactor(health_ratio || "0.00")
      setDepositedData(updatedDepositedData)
      setCurrentSum(current_sum || 0)
      setStartSum(start_sum || 0)     
  }
}, [data,isLoading])



  return {
    cardData,
    healthFactor,
    startSum,
    currentSum,
    depositedData,
    isLoading,
    error,
  }
};

export default useDashboardData;
