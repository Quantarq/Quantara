async function connectWallet() {
    try {
        const starknet = window.starknet;
        const wallet = await starknet.enable();

        if (wallet) {
            console.log("Wallet object:", wallet); // Logs the entire wallet object

            const walletAddress = starknet.selectedAddress;
            console.log("Wallet Address:", walletAddress); // Logs the wallet address
            alert(`Wallet connected: ${walletAddress}`);

            // Save wallet address in session
            const formData = new FormData();
            formData.append("wallet_id", walletAddress);

            await fetch("/login", {
                method: "POST",
                body: formData
            });

            // Redirect or reload the page after connection
            window.location.reload();
        } else {
            alert("Connection failed. Please try again.");
        }
    } catch (error) {
        console.error("Error connecting wallet:", error); // Logs any error
        alert("An error occurred. Please check the console.");
    }
}

async function logout() {
    // Remove wallet_id from session and redirect to login page
    await fetch("/logout", { method: "POST" });
    window.location.href = "/login";
}


async function sendTransaction(transactionData) {
    try {
        const starknet = window.starknet;
        if (!starknet) {
            alert("Please connect to the Argent X wallet.");
            return;
        }

        // Connect to the wallet if not connected
        await connectWallet();

        // Extract approve_data and loop_liquidity_data from transactionData
        const approveData = transactionData[0].approve_data;
        const loopLiquidityData = transactionData[0].loop_liquidity_data;

        // Construct transaction details based on approve data
        const transactionDetails = {
            contractAddress: approveData.to_address,
            entrypoint: "approve",
            calldata: [
                approveData.spender,
                approveData.amount,
            ],
        };

        // Send the transaction via the Starknet provider
        const response = await starknet.provider.invokeFunction(transactionDetails);
        console.log("Transaction response:", response);

        alert(`Transaction sent. Hash: ${response.transaction_hash}`);
    } catch (error) {
        console.error("Error sending transaction:", error);
        alert("An error occurred while sending the transaction.");
    }
}
