import {connect} from "get-starknet";
import {CallData} from "starknet";
import {erc20abi} from "../abis/erc20";
import {abi} from "../abis/abi";

export async function sendTransaction(loopLiquidityData, contractAddress) {
    try {
        const starknet = await connect();
        if (!starknet.isConnected) {
            throw new Error("Wallet not connected");
        }

        if (!loopLiquidityData.pool_key || !loopLiquidityData.deposit_data) {
            throw new Error("Missing or invalid loop_liquidity_data fields");
        }
        console.log(loopLiquidityData)
        let approveCalldata = new CallData(erc20abi);
        const approveTransaction = {
            contractAddress: loopLiquidityData.deposit_data.token,
            entrypoint: "approve",
            calldata: approveCalldata.compile("approve", [
                contractAddress, loopLiquidityData.deposit_data.amount
            ])
        };

        const callData = new CallData(abi);
        const compiled = callData.compile("loop_liquidity", loopLiquidityData);
        const depositTransaction = {
            contractAddress: contractAddress,
            entrypoint: "loop_liquidity",
            calldata: compiled
        };
        let result = await starknet.account.execute([approveTransaction, depositTransaction]);
        console.log("Resp: ")
        console.log(result);
        return {
            loopTransaction: result.transaction_hash
        };
    } catch (error) {
        console.error("Error sending transaction:", error);
        throw error;
    }
}

async function waitForTransaction(txHash) {
    const starknet = await connect();
    let receipt = null;
    while (receipt === null) {
        try {
            receipt = await starknet.provider.getTransactionReceipt(txHash);
        } catch (error) {
            console.log("Waiting for transaction to be accepted...");
            await new Promise(resolve => setTimeout(resolve, 5000)); // Wait for 5 seconds before trying again
        }
    }
    console.log("Transaction accepted:", receipt);
}

export async function closePosition(transactionData, contractAddress) {
    const callData = new CallData(abi);
    const compiled = callData.compile("close_position", transactionData);
    console.log(compiled);
    const starknet = await connect();
    console.log(contractAddress);
    await starknet.account.execute([
        {contractAddress: contractAddress, entrypoint: "close_position", calldata: compiled}]
    );
}
