"use client";

import { useCallback, useEffect, useState } from "react";
import { LibraryError, RpcProvider, constants } from "starknet";
import { ArgentWebWallet, SessionAccountInterface } from "@argent/webwallet-sdk";
// import { toast } from "sonner";


// Initialize argent sdk web wallet session object for telegram mini-dapp
const ARGENT_DUMMY_CONTRACT_ADDRESS = "0x07557a2fbe051e6327ab603c6d1713a91d2cfba5382ac6ca7de884d3278636d7";
const ARGENT_DUMMY_CONTRACT_ENTRYPOINT = "increase_number";

const provider = new RpcProvider({});

const argentWebWallet = ArgentWebWallet.init({
   appName: "hackbot",
   environment: "sepolia", 
   //  | "mainnet" | "dev",
   sessionParams: {
      allowedMethods: [
         {
            contract: ARGENT_DUMMY_CONTRACT_ADDRESS,
            selector: ARGENT_DUMMY_CONTRACT_ENTRYPOINT,
         },
      ],
      validityDays: 10,
   },
   // paymasterParams: {
   //    apiKey: "" // avnu paymasters API Key
   // },
});