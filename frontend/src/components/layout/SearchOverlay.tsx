import React from "react";
import { Dialog } from "@headlessui/react";
import { Search, X } from "lucide-react";
import { useUIStore } from "@/store/uiStore";
import Button from "@/components/ui/Button";

const SearchOverlay: React.FC = () => {
  const { isSearchOpen, closeSearch } = useUIStore();
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (isSearchOpen) {
      const timer = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(timer);
    }
  }, [isSearchOpen]);

  return (
    <Dialog open={isSearchOpen} onClose={closeSearch} className="relative z-50">
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
      <div className="fixed inset-0 flex items-start justify-center p-4">
        <Dialog.Panel className="w-full max-w-xl mt-20 rounded-xl bg-white dark:bg-neutral-900 shadow-2xl border border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center gap-3 p-3 border-b border-neutral-200 dark:border-neutral-700">
            <Search className="w-5 h-5 text-neutral-400" />
            <input
              ref={inputRef}
              type="search"
              placeholder="Search contracts, reports, settings..."
              className="flex-1 bg-transparent outline-none text-neutral-900 dark:text-neutral-100 placeholder-neutral-400"
              aria-label="Global search"
            />
            <Button variant="ghost" size="sm" onClick={closeSearch} aria-label="Close search">
              <X className="w-5 h-5" />
            </Button>
          </div>
          <div className="p-4 text-sm text-neutral-500 dark:text-neutral-400">
            Type to search. Use Enter to submit.
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
};

export default SearchOverlay;

