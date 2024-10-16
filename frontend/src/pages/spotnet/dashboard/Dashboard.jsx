import React, { useEffect, useState } from 'react';
import { ReactComponent as Star } from "../../../assets/particles/star.svg";
import { ReactComponent as CollateralIcon } from "../../../assets/icons/collateral.svg";
import { ReactComponent as EthIcon } from "../../../assets/icons/ethereum.svg";
import { ReactComponent as UsdIcon } from "../../../assets/icons/usd_coin.svg";
import { ReactComponent as BorrowIcon } from "../../../assets/icons/borrow.svg";
import { ReactComponent as StrkIcon } from "../../../assets/icons/strk.svg";
import { closePosition } from "../../../utils/transaction"
import axios from 'axios';
import './dashboard.css';
import {connect} from "get-starknet";

const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://0.0.0.0:8000';

const fetchCardData = async () => { 
    try {
        const starknet = await connect();
        const response = await axios.get(
            `${backendUrl}/api/dashboard?wallet_id=${starknet.selectedAddress}`
        );
        return response.data;
    } catch (error) {
        console.error("Error during getting the data from API", error);
        return null;
    }
};


const Dashboard = () => {
    const closePositionEvent = async (position_id) => {
        try {
            const starknet = await connect();
            const response = await axios.get(
                `${backendUrl}/api/get-repay-data?supply_token=ETH&wallet_id=${starknet.selectedAddress}`
            );
            console.log(response);
            await closePosition(response.data);

            await axios.get(`${backendUrl}/api/close-position?position_id=${position_id}`);
        } catch (e) {
            console.log(e);
        }
    };

    const [cardData, setCardData] = useState([]);
    const [healthFactor, setHealthFactor] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);


    const starData = [
        { top: 1, left: 0, size: 1.5 },
        { top: 75, left: 35, size: 2.5 },
        { top: -2, left: 94, size: 5.5 },
    ];

    useEffect(() => {
        const getData = async () => {
            const data = await fetchCardData();
            
            if (data && data.zklend_position && data.zklend_position.products) {
                const positions = data.zklend_position.products[0].positions || [];
                const healthRatio = data.zklend_position.products[0].health_ratio || 0;

            const cardData = positions.map((position, index) => {
                const isFirstCard = index === 0;
                const tokenAddress = position.tokenAddress;

                if (isFirstCard) {
                    const isEthereum = tokenAddress === "0x01b5bd713e72fdc5d63ffd83762f81297f6175a5e0a4771cdadbc1dd5fe72cb1";
                    return {
                        position_id: position.position_id,
                        title: "Collateral & Earnings",
                        icon: CollateralIcon,
                        balance: position.totalBalances[Object.keys(position.totalBalances)[0]] || 0,
                        currencyName: isEthereum ? "Ethereum" : "STRK",
                        currencyIcon: isEthereum ? EthIcon : StrkIcon,
                    };
                }

                return {
                    position_id: position.position_id,
                    title: "Borrow",
                    icon: BorrowIcon,
                    balance: position.totalBalances[Object.keys(position.totalBalances)[0]] || 0,
                    currencyName: "USD Coin",
                    currencyIcon: UsdIcon,
                };
            });

                setCardData(cardData);
                setHealthFactor(healthRatio);
                setError(false);
            } else {
                console.error("Data is missing or incorrectly formatted");
                setError(true);
                setCardData([]);
                setHealthFactor(0);
            }
            setLoading(false);
            };

            const timeoutId = setTimeout(() => {
                if (loading) {
                    setError(true);
                    setLoading(false);
                    setCardData([]);
                    setHealthFactor(0); 
                }
            }, 100000);

        getData();

        return () => clearTimeout(timeoutId);
    }, []);

    if (loading) {
        return <div className="d-flex text-white justify-content-center align-items-center min-vh-100">Loading...</div>;
    }

    if (!cardData.length) {
        return <div className="text-white text-center min-vh-100 d-flex align-items-center justify-content-center">Error during getting the data. Please try again later.</div>;
    }

    return (
        <div className="dashboard-container position-relative container">
            {starData.map((star, index) => (
                <Star key={index} style={{
                    position: 'absolute',
                    top: `${star.top}%`,
                    left: `${star.left}%`,
                    width: `${star.size}%`,
                    height: `${star.size}%`
                }}/>
            ))}
            <div className="backdround-gradients position-relative">
                <div className="backdround-gradient"></div>
                <div className="backdround-gradient"></div>
            </div>
            <h1 className="text-white text-center zkLend-text">
                zkLend Position
            </h1>
            <div className="card card-health-factor mx-auto d-flex flex-column align-items-center justify-content-center card-shadow">
                <div className="content bg-custom-health d-flex align-items-center px-4 py-3 rounded bg-card-health">
                    <span className="dashboard-text-color health-text-size">
                        Health factor:
                    </span>
                    <span className="text-white text-style">
                        {healthFactor}
                    </span>
                </div>
            </div>
            <div className="mb-4 d-flex flex-row justify-content-center cards-custom">
                {cardData.map((card, index) => (
                    <div key={index} className="card card-custom-styles d-flex flex-column align-item-center card-shadow">
                        <header className="card-header bg-custom-color text-light text-center card-shadow">
                            <div className="d-flex align-items-center justify-content-center">
                                <card.icon className="card-icons rounded-circle" />
                                <h1 className="ms-2 icon-text-gap mb-0 text-style"
                                    style={{ color: card.title === "Borrow" ? "var(--borrow-color)" : "var(--collateral-color)" }}>
                                    {card.title}
                                </h1>
                            </div>
                        </header>
                        <div className="card-body card-body-custom">
                            <div className="d-flex flex-column align-items-center bg-custom-color rounded">
                                <div className="d-flex align-items-center mb-3">
                                    <card.currencyIcon className="card-icons rounded-circle" />
                                    <span className="ms-2 icon-text-gap text-style">{card.currencyName}</span>
                                </div>
                                <div className="d-flex align-items-center">
                                    <span className="dashboard-text-color balance-text-size">Balance:</span>
                                    <span className="ms-2 borr-text icon-text-gap text-style" style={{
                                        color: card.title === "Borrow" ? "var(--borrow-color)" : "var(--collateral-color)" }}>
                                        {card.balance}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div className="card-footer text-center">
                            <button
                                className="btn redeem-btn border-0"
                                onClick={() => closePositionEvent(card.position_id)}
                            >
                                Redeem
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Dashboard;