import { useMutation } from "@tanstack/react-query";
import { subscribeToNotification } from "services/telegram";
import { notifyError, notifySuccess } from "utils/notification";

const useTelegramNotification = () => {
    const mutation = useMutation({
        mutationFn: ({ telegramId, walletId }) =>
            subscribeToNotification(telegramId, walletId),
        onSuccess: () => {
            notifySuccess("Subscribed to notifications successfully!");
        },
        onError: (error) => {
            notifyError(error?.message || "Failed to subscribe. Please try again.");
        },
    });

    return {
        subscribe: mutation.mutate,
        isLoading: mutation.isPending,
    };
};

export default useTelegramNotification;
