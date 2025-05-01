import Link from "next/link";

export default function Terms() {
  return (
    <div className="w-full h-full bg-[#000A0F]">
      <div className="max-w-7xl mx-auto p-8 md:p-20">
        <div className="pt-10 space-y-5 items-start">
          <h1 className="text-4xl font-bold">Terms & Conditions</h1>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">Acceptance of Terms</h2>
          <p className="text-md">
            By accessing, browsing, or using this website, you acknowledge that
            you have read, understood, and agree to be bound by these terms and
            any applicable laws or regulations. If you do not agree to these
            terms, then please do not use this website.
          </p>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">Changes and Amendments</h2>
          <p className="text-md">
            We reserve the right to modify these terms and conditions at any
            time, without notice, and such modifications shall be effective
            immediately upon posting of the modified terms. Your continued use
            of this website will signify your acceptance of these changes.
          </p>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">Privacy Policy</h2>
          <p className="text-md">
            Our Privacy Policy, which sets out how we will use your information,
            can be found in our
            <Link
              href="/policies/privacy"
              className="text-blue-500 hover:text-blue-400"
            >
              {" "}
              Privacy Policy
            </Link>
            . By using this website, you consent to the processing described
            therein and warrant that all data provided by you is accurate.
          </p>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">Prohibited Conduct</h2>
          <p className="text-md">
            You are expressly prohibited from using this website for any of the
            following:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Any unlawful purposes.</li>
            <li>Compromising the security of the website.</li>
            <li>
              Copying, transmitting, distributing, or creating derivative works
              of the content without our permission.
            </li>
            <li>
              Using this website in a way that may damage or impair the website,
              or interfere with anyone else&apos;s use and enjoyment of the
              website.
            </li>
          </ul>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">Intellectual Property</h2>
          <p className="text-md">
            The intellectual property rights in all content and materials on the
            website are owned by us or our licensors. You are granted a limited
            license only, subject to the restrictions provided in these terms,
            for purposes of viewing the material contained on this website.
          </p>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">User Content</h2>
          <p className="text-md">
            In these terms and conditions, &quot;your user content&quot; means
            material (including but not limited to text, images, audio material,
            video material, and audio-visual material) that you submit to this
            website, for whatever purpose. You grant to us a worldwide,
            irrevocable, non-exclusive, royalty-free license to use, reproduce,
            adapt, publish, translate, and distribute your user content in any
            existing or future media. You also grant us the right to sub-license
            these rights and the right to bring an action for infringement of
            these rights.
          </p>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">No Warranties</h2>
          <p className="text-md">
            This website is provided &quot;as is,&quot; with all faults, and we
            express no representations or warranties, of any kind related to
            this website or the materials contained on this website. Also,
            nothing contained on this website shall be interpreted as advising
            you.
          </p>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">Limitation of Liability</h2>
          <p className="text-md">
            In no event shall we, nor any of our officers, directors, and
            employees, be liable to you for anything arising out of or in any
            way connected with your use of this website, whether such liability
            is under contract, tort, or otherwise, and we, including our
            officers, directors, and employees shall not be liable for any
            indirect, consequential, or special liability arising out of or in
            any way related to your use of this website.
          </p>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">Indemnification</h2>
          <p className="text-md">
            You hereby indemnify us to the fullest extent from and against any
            and all liabilities, costs, demands, causes of action, damages, and
            expenses (including reasonable attorney&apos;s fees) arising out of
            or in any way related to your breach of any of the provisions of
            these terms.
          </p>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">Severability</h2>
          <p className="text-md">
            If any provision of these terms is found to be unenforceable or
            invalid under any applicable law, such unenforceability or
            invalidity shall not render these terms unenforceable or invalid as
            a whole, and such provisions shall be deleted without affecting the
            remaining provisions herein.
          </p>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">Entire Agreement</h2>
          <p className="text-md">
            These terms, including any legal notices and disclaimers contained
            on this website, constitute the entire agreement between us and you
            in relation to your use of this website, and supersede all prior
            agreements and understandings with respect to the same.
          </p>
          <hr className="my-4 border-gray-700" />

          <h2 className="text-2xl font-semibold">
            Governing Law & Jurisdiction
          </h2>
          <p className="text-md">
            These terms will be governed by and construed in accordance with the
            laws of California, and you submit to the non-exclusive jurisdiction
            of the state and federal courts located in California for the
            resolution of any disputes.
          </p>

          <h2 className="text-2xl font-semibold">Contact Information</h2>
          <p className="text-md">
            If you have any questions about these Terms, please contact us at:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Email: legal@speck.sh</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
