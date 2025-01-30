import React from 'react';
import SettingIcon from '@/assets/icons/settings.svg?react';
import './gasFee.css';

export default function GasFee() {
  return (
    <div className="main-card-footer">
      <div className="gas-fee-container w-full flex flex-row  items-center justify-between gap-2 py-3 px-2 border-t border-[#36294E] " style={{justifyContent: "space-between"}}>
        <div className="gas-fee-circle">
          <SettingIcon className="gas-fee-icon" />
        </div>
        <div className="gas-fee-title text-sm text-[#83919F] font-normal ">Gas fee: 0.00 STRK</div>
      </div>
    </div>
  );
}
