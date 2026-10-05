import { CustomerSearch } from "../components/CustomerSearch";
import { PageHeader } from "@/shared/ui/page-header";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";

export default function CustomerSearchPage() {
  return (
    <main className="ns-page space-y-5">
      <PageHeader
        eyebrow="Ops console"
        title="Customers"
        desc="Look-alike names included on purpose — verify identity against the ticket before acting."
      />
      <Card lift={false}>
        <CardHeader title="Directory" desc="Name, email or customer code." />
        <CardBody>
          <CustomerSearch />
        </CardBody>
      </Card>
    </main>
  );
}
