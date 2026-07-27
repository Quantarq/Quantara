import React, { useState, useRef } from 'react';
import { useAddressBookStore } from '@/stores/useAddressBookStore';

function truncateAddress(addr) {
  if (addr.length <= 16) return addr;
  return `${addr.slice(0, 8)}...${addr.slice(-6)}`;
}

function AddressBook() {
  const { addresses, addAddress, removeAddress, exportAddresses, importAddresses } =
    useAddressBookStore();
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [importMessage, setImportMessage] = useState(null);
  const fileInputRef = useRef(null);

  const handleAdd = (e) => {
    e.preventDefault();
    if (!name.trim() || !address.trim()) return;
    const success = addAddress(name, address);
    if (!success) {
      setImportMessage({ success: false, message: 'Address already exists' });
      setTimeout(() => setImportMessage(null), 3000);
      return;
    }
    setName('');
    setAddress('');
  };

  const handleExport = () => {
    const json = exportAddresses();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'quantara-address-book.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const result = importAddresses(event.target.result);
      setImportMessage(result);
      setTimeout(() => setImportMessage(null), 4000);
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleCopy = (addr) => {
    navigator.clipboard.writeText(addr);
  };

  return (
    <div className="flex flex-col gap-6 w-full">
      <form onSubmit={handleAdd} className="flex flex-col gap-3">
        <input
          type="text"
          placeholder="Name (e.g. My Wallet)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded-lg border border-[#300734] bg-transparent px-4 py-3 text-sm text-white placeholder-gray outline-none focus:border-[#a855f7] transition-colors"
        />
        <input
          type="text"
          placeholder="Wallet address (0x...)"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          className="w-full rounded-lg border border-[#300734] bg-transparent px-4 py-3 text-sm text-white placeholder-gray outline-none focus:border-[#a855f7] transition-colors"
        />
        <button
          type="submit"
          disabled={!name.trim() || !address.trim()}
          className="w-full rounded-lg border border-[#a855f7] bg-transparent py-3 text-sm font-semibold text-white transition-colors hover:bg-[#a855f7]/20 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          Add Address
        </button>
      </form>

      <div className="flex gap-2">
        <button
          onClick={handleExport}
          disabled={addresses.length === 0}
          className="flex-1 rounded-lg border border-light-purple bg-transparent py-2.5 text-xs font-semibold text-white transition-colors hover:border-[#a855f7] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          Export JSON
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex-1 rounded-lg border border-light-purple bg-transparent py-2.5 text-xs font-semibold text-white transition-colors hover:border-[#a855f7] cursor-pointer"
        >
          Import JSON
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={handleImport}
          className="hidden"
        />
      </div>

      {importMessage && (
        <div
          className={`rounded-lg px-4 py-2.5 text-xs ${
            importMessage.success
              ? 'border border-green-500/40 text-green-400'
              : 'border border-red-500/40 text-red-400'
          }`}
        >
          {importMessage.message}
        </div>
      )}

      {addresses.length === 0 ? (
        <p className="text-center text-sm text-gray py-8">
          No saved addresses yet. Add one above or import from a JSON file.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {addresses.map((entry) => (
            <div
              key={entry.id}
              className="flex items-center justify-between rounded-lg border border-[#300734] bg-transparent px-4 py-3"
            >
              <div className="flex flex-col gap-0.5 min-w-0">
                <span className="text-sm font-semibold text-white truncate">
                  {entry.name}
                </span>
                <button
                  onClick={() => handleCopy(entry.address)}
                  className="text-xs text-gray hover:text-[#a855f7] transition-colors cursor-pointer text-left truncate max-w-[260px]"
                  title="Click to copy"
                >
                  {truncateAddress(entry.address)}
                </button>
              </div>
              <button
                onClick={() => removeAddress(entry.id)}
                className="ml-3 shrink-0 text-xs text-red-400 hover:text-red-300 transition-colors cursor-pointer px-2 py-1"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AddressBook;
