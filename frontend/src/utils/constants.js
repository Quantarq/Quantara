import {CallData} from "starknet";
import {abi} from "../abis/abi";

export const CONTRACT_ADDRESS = "0x041a78e741e5af2fec34b695679bc6891742439f7afb8484ecd7766661ad02bf";
export const CLASS_HASH = "0x07898133aa022d3bc986f9397606990a5f64628e8e6a0aaa23cb91fb7b325d9e";
export const UNIQUE = "0x0";
export const EKUBO_ADDRESS =  "0x00000005dd3d2f4429af886cd1a3b08289dbcea99a294197e9eb43b0e0325b4b"
export const ZKLEND_ADDRESS = "0x04c0a5193d58f74fbace4b74dcf65481e734ed1714121bdc571da345540efa05"


export function getDeployContractData(walletId) {
    return {
        classHash: CLASS_HASH,
        salt: `0x${Math.floor(Math.random() * 1e16).toString(16)}`, // Generate random salt
        unique: false,
        constructorCalldata: [
            walletId,
            EKUBO_ADDRESS,
            ZKLEND_ADDRESS
        ]
    };
}
