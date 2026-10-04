import { CustomerSearch } from "../components/CustomerSearch";

export default function CustomerSearchPage() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Customers</h1>
      <div className="mt-4">
        <CustomerSearch />
      </div>
    </main>
  );
}
