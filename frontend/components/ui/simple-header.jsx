import React from 'react'; 
import { Button, buttonVariants } from '@/components/ui/button';
import Image from 'next/image';

export function SimpleHeader() {

	const links = [
		{
			label: 'Features',
			href: '#',
		},
		{
			label: 'Pricing',
			href: '#',
		},
		{
			label: 'About',
			href: '#',
		},
	];

	return (
        <header
            className="bg-background/95 sticky top-1/4 z-50 w-full backdrop-blur-lg">
            <nav
                className="mx-auto flex h-20 w-full max-w-4xl items-center justify-between px-4">
				<div className="flex items-center gap-2">
					<Image 
					src={"/logo.png"}
					width={70}
					height={70}
					/>
				</div>
				<div className="hidden items-center gap-2 lg:flex">
					{links.map((link) => (
						<a className={buttonVariants({ variant: 'ghost' })} href={link.href}>
							{link.label}
						</a>
					))}
					<Button variant="outline">Sign In</Button>
					<Button>Get Started</Button>
				</div>
				{/* <Sheet>
					<Button size="icon" variant="outline" className="lg:hidden">
						<MenuToggle strokeWidth={2.5} open={open} onOpenChange={setOpen} className="size-6" />
					</Button>
				</Sheet> */}
			</nav>
        </header>
    );
}
