console.log("JavaScript is loaded");
alert("JavaScript is working!");

// Update max balance based on the selected token
function updateMaxBalance() {
    const selectedToken = document.getElementById('token').value;
    const maxBalance = balances[selectedToken] || 0;
    document.getElementById('amount').setAttribute('max', maxBalance);
}

// Validate the entered amount
// function validateAmount() {
//     const selectedToken = document.getElementById("token").value;
//     const enteredAmount = parseFloat(document.getElementById("amount").value);
//     const maxBalance = balances[selectedToken] || 0;
//
//     if (enteredAmount > maxBalance) {
//         document.getElementById("balance-warning").style.display = "block";
//         return false;
//     } else {
//         document.getElementById("balance-warning").style.display = "none";
//         return true;
//     }
// }

document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM Content Loaded");

    // Attach change event to token select dropdown
    // document.getElementById("token").addEventListener("change", updateMaxBalance);

    // Attach click event to submit button
    document.getElementById("submit-btn").onclick = async function () {
        console.log("Submit button clicked");

        // Get form values
        const token = document.getElementById("token").value;
        const amount = document.getElementById("amount").value;
        const multiplier = document.getElementById("multiplier").value;

        console.log("Form Values:", { token, amount, multiplier });

        try {
            const response = await fetch(`/transaction-data?token=${token}&amount=${amount}&multiplier=${multiplier}`, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                },
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`Failed to fetch transaction data: ${errorData.message || "Unknown error"}`);
            }

            const transactionData = await response.json();
            console.log("Transaction data received:", transactionData);

            // Implement sendTransaction here
            await sendTransaction(transactionData);
        } catch (error) {
            console.error("Error while submitting form:", error.message);
            alert(`Failed to submit the form and fetch transaction data: ${error.message}`);
        }
    };
});
