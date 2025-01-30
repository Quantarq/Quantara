import React from 'react';
import SettingIcon from '@/assets/icons/settings.svg?react';

export default function GasFee() {
  return (
    <div className="w-full flex flex-row  items-center justify-between gap-2 py-3 px-2 border-t border-light-purple">
      <div className="bg-footer-divider rounded-full p-2">
        <SettingIcon />
      </div>
      <div className="text-sm text-[#83919F] font-normal ">Gas fee: 0.00 STRK</div>
    </div>
  );
}
