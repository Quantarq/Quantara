import { create } from 'zustand';

const STORAGE_KEY = 'quantara-address-book';

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveToStorage(addresses) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(addresses));
}

let nextId = Date.now();

export const useAddressBookStore = create((set, get) => ({
  addresses: loadFromStorage(),

  addAddress: (name, address) => {
    const trimmed = address.trim();
    const exists = get().addresses.some(
      (a) => a.address.toLowerCase() === trimmed.toLowerCase()
    );
    if (exists) return false;

    const entry = {
      id: String(nextId++),
      name: name.trim(),
      address: trimmed,
      createdAt: new Date().toISOString(),
    };
    const updated = [...get().addresses, entry];
    saveToStorage(updated);
    set({ addresses: updated });
    return true;
  },

  removeAddress: (id) => {
    const updated = get().addresses.filter((a) => a.id !== id);
    saveToStorage(updated);
    set({ addresses: updated });
  },

  exportAddresses: () => {
    const data = {
      version: 1,
      addresses: get().addresses,
    };
    return JSON.stringify(data, null, 2);
  },

  importAddresses: (jsonString) => {
    try {
      const parsed = JSON.parse(jsonString);
      if (!parsed.addresses || !Array.isArray(parsed.addresses)) {
        return { success: false, message: 'Invalid file format' };
      }

      const existing = get().addresses;
      const existingSet = new Set(
        existing.map((a) => a.address.toLowerCase())
      );
      let imported = 0;

      for (const addr of parsed.addresses) {
        if (!addr.address || !addr.name) continue;
        if (existingSet.has(addr.address.toLowerCase())) continue;
        existingSet.add(addr.address.toLowerCase());
        existing.push({
          id: String(nextId++),
          name: addr.name,
          address: addr.address,
          createdAt: addr.createdAt || new Date().toISOString(),
        });
        imported++;
      }

      saveToStorage(existing);
      set({ addresses: [...existing] });
      return {
        success: true,
        message: `Imported ${imported} address(es), skipped ${parsed.addresses.length - imported} duplicate(s)`,
      };
    } catch {
      return { success: false, message: 'Failed to parse JSON' };
    }
  },
}));
