import Link from "next/link";
import "../styles/globals.css";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Hero Section */}
      <section className="relative px-6 lg:px-8 pt-20 pb-32">
        <div className="mx-auto max-w-7xl">
          <div className="text-center">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
              Transform your personal training practice with{" "}
              <span className="text-blue-600">AI-powered session summaries</span> and client insights
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600 max-w-3xl mx-auto">
              Save hours every week with intelligent session transcriptions, automated client progress tracking, 
              and actionable training insights. Transform scattered workout notes into organized, 
              professional client management that drives results and keeps your clients motivated.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Link
                href="/waitlist"
                className="rounded-md ci-bg-primary px-6 py-3 text-lg font-semibold ci-text-white shadow-sm hover:ci-bg-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
              >
                Join Waitlist
              </Link>
              <Link
                href="#features"
                className="text-lg font-semibold leading-6 text-gray-900 hover:text-blue-600"
              >
                Learn more <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Problem-Solution Section */}
      <section className="py-24 bg-white">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl lg:text-center">
            <h2 className="text-base font-semibold leading-7 text-blue-600">The Problem</h2>
            <p className="mt-2 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Personal training shouldn&apos;t be buried in paperwork
            </p>
          </div>
          
          <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
            <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-3">
              <div className="flex flex-col">
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                  <div className="h-5 w-5 flex-none rounded-full bg-red-500"></div>
                  Manual Note-Taking
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                  <p className="flex-auto">
                    Spending hours after each training session writing up notes, trying to remember client progress, 
                    and tracking workout results manually steals time from what matters most - training clients.
                  </p>
                </dd>
              </div>
              
              <div className="flex flex-col">
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                  <div className="h-5 w-5 flex-none rounded-full bg-red-500"></div>
                  Scattered Information
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                  <p className="flex-auto">
                    Client workout data spread across notebooks, apps, and memory makes it impossible 
                    to track progress effectively and provide consistent, personalized training programs.
                  </p>
                </dd>
              </div>
              
              <div className="flex flex-col">
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                  <div className="h-5 w-5 flex-none rounded-full bg-red-500"></div>
                  Missed Opportunities
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                  <p className="flex-auto">
                    Important training milestones and breakthrough moments get lost in the shuffle, 
                    reducing client motivation and the effectiveness of your training programs.
                  </p>
                </dd>
              </div>
            </dl>
          </div>

          <div className="mx-auto mt-16 max-w-2xl lg:text-center">
            <h3 className="mt-2 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              <span className="text-blue-600">CoachIntel</span> puts everything in its place
            </h3>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              Our AI automatically captures, organizes, and analyzes your training sessions, 
              giving you more time to focus on what you do best - transforming your clients&apos; fitness journeys.
            </p>
          </div>
        </div>
      </section>

      {/* Core Features Section */}
      <section id="features" className="py-24 bg-gray-50">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl lg:text-center">
            <h2 className="text-base font-semibold leading-7 text-blue-600">Core Features</h2>
            <p className="mt-2 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Everything you need to scale your personal training business
            </p>
          </div>
          
          <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
            <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-2">
              <div className="flex flex-col">
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                  <div className="h-10 w-10 flex items-center justify-center rounded-lg ci-bg-primary">
                    <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  Automated Session Transcriptions
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                  <p className="flex-auto">
                    Seamlessly integrate with your existing tools like Fireflies and Google Calendar. 
                    Every training session is automatically transcribed and organized without any manual work.
                  </p>
                </dd>
              </div>
              
              <div className="flex flex-col">
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                  <div className="h-10 w-10 flex items-center justify-center rounded-lg ci-bg-primary">
                    <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3-9v11.25A2.25 2.25 0 0116.5 21h-7.5A2.25 2.25 0 017 18.75V4.5a2.25 2.25 0 012.25-2.25h7.5A2.25 2.25 0 0118.75 4.5V9M9 7.5h3.75m0 0l1.5-1.5M12.75 6v1.5m0 0l1.5-1.5" />
                    </svg>
                  </div>
                  Intelligent Client Progress Tracking
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                  <p className="flex-auto">
                    AI analyzes your sessions to create comprehensive client fitness profiles, tracking workout progress, 
                    goals, and breakthrough moments so you&apos;re always prepared for the next training session.
                  </p>
                </dd>
              </div>
              
              <div className="flex flex-col">
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                  <div className="h-10 w-10 flex items-center justify-center rounded-lg ci-bg-primary">
                    <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
                    </svg>
                  </div>
                  Actionable Training Insights
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                  <p className="flex-auto">
                    Get AI-powered insights and recommendations based on client workout patterns, helping you 
                    identify the most effective exercises and training progressions for each individual.
                  </p>
                </dd>
              </div>
              
              <div className="flex flex-col">
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                  <div className="h-10 w-10 flex items-center justify-center rounded-lg ci-bg-primary">
                    <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
                    </svg>
                  </div>
                  Seamless Integrations
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                  <p className="flex-auto">
                    Works with the tools you already use: Fireflies, Google Calendar, Zoom, and more. 
                    No workflow disruption - just enhanced productivity from day one.
                  </p>
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      {/* Social Proof Section */}
      <section className="py-24 bg-white">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl lg:text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Trusted by personal trainers and fitness coaches
            </h2>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              See what early adopters are saying about CoachIntel
            </p>
          </div>
          
          <div className="mx-auto mt-16 flow-root max-w-2xl sm:mt-20 lg:mx-0 lg:max-w-none">
            <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-2xl bg-gray-50 p-8">
                <figure>
                  <blockquote className="text-gray-900">
                    <p>
                      &quot;CoachIntel has transformed how I manage my client relationships. 
                      I save 3-4 hours per week on admin work and my clients love the 
                      detailed session summaries and progress tracking I can now provide.&quot;
                    </p>
                  </blockquote>
                  <figcaption className="mt-6 flex items-center gap-x-4">
                    <div className="h-10 w-10 rounded-full ci-bg-primary flex items-center justify-center">
                      <span className="text-white font-semibold">SK</span>
                    </div>
                    <div>
                      <div className="font-semibold">Sarah Kim</div>
                      <div className="text-gray-600">Personal Trainer, 8+ years</div>
                    </div>
                  </figcaption>
                </figure>
              </div>
              
              <div className="rounded-2xl bg-gray-50 p-8">
                <figure>
                  <blockquote className="text-gray-900">
                    <p>
                      &quot;The AI insights are incredibly accurate. It picks up on training patterns 
                      I sometimes miss and suggests workout modifications that have led to 
                      amazing results with my clients.&quot;
                    </p>
                  </blockquote>
                  <figcaption className="mt-6 flex items-center gap-x-4">
                    <div className="h-10 w-10 rounded-full ci-bg-primary flex items-center justify-center">
                      <span className="text-white font-semibold">MR</span>
                    </div>
                    <div>
                      <div className="font-semibold">Michael Rodriguez</div>
                      <div className="text-gray-600">Fitness Coach, 12+ years</div>
                    </div>
                  </figcaption>
                </figure>
              </div>
              
              <div className="rounded-2xl bg-gray-50 p-8">
                <figure>
                  <blockquote className="text-gray-900">
                    <p>
                      &quot;Setup was incredibly easy - connected my existing tools in minutes. 
                      Now every training session is automatically organized and I never miss 
                      important client milestones or follow-ups.&quot;
                    </p>
                  </blockquote>
                  <figcaption className="mt-6 flex items-center gap-x-4">
                    <div className="h-10 w-10 rounded-full ci-bg-primary flex items-center justify-center">
                      <span className="text-white font-semibold">JC</span>
                    </div>
                    <div>
                      <div className="font-semibold">Jennifer Chen</div>
                      <div className="text-gray-600">Strength Coach, 6+ years</div>
                    </div>
                  </figcaption>
                </figure>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-24 bg-gray-50">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl sm:text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Simple, transparent pricing
            </h2>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              Special early adopter pricing - lock in these rates for life
            </p>
          </div>
          
          <div className="mx-auto mt-16 max-w-2xl rounded-3xl ring-1 ring-gray-200 sm:mt-20 lg:mx-0 lg:max-w-none">
            <div className="p-8 sm:p-10 lg:flex-auto">
              <h3 className="text-2xl font-bold tracking-tight text-gray-900">Early Adopter Plan</h3>
              <p className="mt-6 text-base leading-7 text-gray-600">
                Everything you need to transform your personal training practice with AI-powered automation.
              </p>
              <div className="mt-10 flex items-center gap-x-4">
                <h4 className="flex-none text-sm font-semibold leading-6 text-blue-600">What&apos;s included</h4>
                <div className="h-px flex-auto bg-gray-100"></div>
              </div>
              <ul className="mt-8 grid grid-cols-1 gap-4 text-sm leading-6 text-gray-600 sm:grid-cols-2 sm:gap-6">
                <li className="flex gap-x-3">
                  <svg className="h-6 w-5 flex-none text-blue-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                  </svg>
                  Unlimited session transcriptions
                </li>
                <li className="flex gap-x-3">
                  <svg className="h-6 w-5 flex-none text-blue-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                  </svg>
                  AI-powered client summaries
                </li>
                <li className="flex gap-x-3">
                  <svg className="h-6 w-5 flex-none text-blue-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                  </svg>
                  Coaching insights &amp; suggestions
                </li>
                <li className="flex gap-x-3">
                  <svg className="h-6 w-5 flex-none text-blue-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                  </svg>
                  Calendar &amp; tool integrations
                </li>
                <li className="flex gap-x-3">
                  <svg className="h-6 w-5 flex-none text-blue-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                  </svg>
                  Priority support
                </li>
                <li className="flex gap-x-3">
                  <svg className="h-6 w-5 flex-none text-blue-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                  </svg>
                  Rate locked for life
                </li>
              </ul>
            </div>
            <div className="-mt-2 p-2 lg:mt-0 lg:w-full lg:max-w-md lg:flex-shrink-0">
              <div className="rounded-2xl bg-gray-50 py-10 text-center ring-1 ring-inset ring-gray-900/5 lg:flex lg:flex-col lg:justify-center lg:py-16">
                <div className="mx-auto max-w-xs px-8">
                  <p className="text-base font-semibold text-gray-600">Early Adopter Special</p>
                  <p className="mt-6 flex items-baseline justify-center gap-x-2">
                    <span className="text-5xl font-bold tracking-tight text-gray-900">$49</span>
                    <span className="text-sm font-semibold leading-6 tracking-wide text-gray-600">/month</span>
                  </p>
                  <p className="mt-2 text-xs leading-5 text-gray-600">
                    <span className="line-through">Regular price: $99/month</span>
                  </p>
                  <Link
                    href="/waitlist"
                    className="mt-10 block w-full rounded-md ci-bg-primary px-3 py-2 text-center text-sm font-semibold text-white shadow-sm hover:ci-bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                  >
                    Join Waitlist
                  </Link>
                  <p className="mt-6 text-xs leading-5 text-gray-600">
                    14-day free trial • No credit card required
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-24 bg-white">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl lg:text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Frequently asked questions
            </h2>
          </div>
          
          <div className="mx-auto mt-16 max-w-2xl divide-y divide-gray-100">
            <div className="py-6">
              <dt className="text-base font-semibold leading-7 text-gray-900">
                How complex is the integration setup?
              </dt>
              <dd className="mt-2 text-base leading-7 text-gray-600">
                Extremely simple. Most coaches are up and running in under 5 minutes. We provide 
                one-click integrations with popular tools like Fireflies, Google Calendar, and Zoom. 
                Our setup wizard guides you through each step.
              </dd>
            </div>
            
            <div className="py-6">
              <dt className="text-base font-semibold leading-7 text-gray-900">
                How secure is my client data?
              </dt>
              <dd className="mt-2 text-base leading-7 text-gray-600">
                Security is our top priority. All data is encrypted in transit and at rest, and 
                we never share or sell your data. You maintain full ownership and control of all 
                client information with regular security updates and monitoring.
              </dd>
            </div>
            
            <div className="py-6">
              <dt className="text-base font-semibold leading-7 text-gray-900">
                What if I need to export my data?
              </dt>
              <dd className="mt-2 text-base leading-7 text-gray-600">
                You own your data completely. Export everything at any time in standard formats 
                (PDF, CSV, JSON). There are no lock-in periods or export fees - your data remains 
                yours forever.
              </dd>
            </div>
            
            <div className="py-6">
              <dt className="text-base font-semibold leading-7 text-gray-900">
                Do you support different types of fitness coaches?
              </dt>
              <dd className="mt-2 text-base leading-7 text-gray-600">
                Yes! CoachIntel works for personal trainers, fitness coaches, strength coaches, 
                sports performance coaches, and more. Our AI adapts to your training style and terminology 
                over time for increasingly personalized insights.
              </dd>
            </div>
            
            <div className="py-6">
              <dt className="text-base font-semibold leading-7 text-gray-900">
                Can I cancel anytime?
              </dt>
              <dd className="mt-2 text-base leading-7 text-gray-600">
                Absolutely. No contracts, no cancellation fees. If you&apos;re not satisfied, 
                you can cancel with one click. Early adopters who choose to stay keep their 
                discounted rate forever.
              </dd>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section className="ci-bg-primary">
        <div className="px-6 py-24 sm:px-6 sm:py-32 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Ready to transform your personal training practice?
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-blue-200">
              Join hundreds of personal trainers who are already saving hours every week with CoachIntel. 
              Be first to get access when we open.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Link
                href="/waitlist"
                className="rounded-md bg-white px-6 py-3 text-lg font-semibold text-blue-600 shadow-sm hover:bg-blue-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
              >
                Join Waitlist
              </Link>
              <Link
                href="/login"
                className="text-lg font-semibold leading-6 text-white hover:text-blue-100"
              >
                Already have an account? Sign in <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
