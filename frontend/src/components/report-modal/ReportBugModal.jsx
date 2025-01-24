import React, { useState } from "react";
import "./ReportBugModal.css";
import telegramIcon from "../../assets/icons/telegram.svg";
import bg from "../../assets/images/background-form.png";
import { Button } from "components/ui/custom-button/Button";
import { useWalletStore } from "../../stores/useWalletStore";
import { useMutation } from "@tanstack/react-query";
import { generateTelegramLink } from "services/telegram";
import { axiosInstance } from "utils/axios";
import { notify } from "components/layout/notifier/Notifier";

export function ReportBugModal({ onClose }) {
    const { walletId } = useWalletStore();
    const [bugDescription, setBugDescription] = useState("");

    const mutation = useMutation({
        mutationFn: async () => {
            if (!window?.Telegram?.WebApp?.initData?.user?.id) {
                const { subscription_link } = await generateTelegramLink(walletId);
                window.open(subscription_link, "_blank");
                return;
            }
            // Send bug report
            return await axiosInstance.post(`/api/save-bug-report`, {
                telegram_id: window?.Telegram?.WebApp?.initData?.user?.id,
                wallet_id: walletId,
                bug_description: bugDescription,
            });
        },
        onSuccess: () => {
            notify("Report sent successfully!");
        },
        onError: (error) => {
            notify(error.response?.data?.message || "Report failed!", "error");
        },
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!bugDescription.trim()) {
            notify("Bug description cannot be empty!", "error");
            return;
        }
        mutation.mutate();
        onClose();
    };

    return (
        <div
            onClick={onClose}
            style={{ backgroundImage: `url(${bg})`, backgroundSize: "contain" }}
            className="modal-overlay"
        >
            <form
                className="report-bug-form"
                onClick={(e) => e.stopPropagation()}
                onSubmit={handleSubmit}
            >
                <div className="modal-content">
                    <h3>Report Bug</h3>
                    <p className="modal-paragraph-text">
                        Please describe the bug you've encountered
                    </p>
                    <textarea
                        value={bugDescription}
                        onChange={(e) => setBugDescription(e.target.value)}
                        placeholder="The bug I'm experiencing..."
                        className="bug-textarea"
                        required
                    />
                    <a
                        className="dev-group-link"
                        href="https://t.me/spotnet_dev"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        <img
                            src={telegramIcon}
                            alt="telegram-icon"
                            className="telegram-icon"
                        />
                        Ask in our Dev group
                    </a>
                </div>
                <div className="button-group">
                    <Button
                        variant="secondary"
                        type="button"
                        className="cancel-button"
                        onClick={(e) => {
                            e.stopPropagation();
                            onClose();
                        }}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="primary"
                        type="submit"
                        className="submit-button"
                    >
                        {mutation.isLoading ? "Sending..." : "Send Report"}
                    </Button>
                </div>
            </form>
        </div>
    );
}
