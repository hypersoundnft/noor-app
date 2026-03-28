"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Carousel, CarouselApi, CarouselContent, CarouselItem } from "@/components/ui/carousel";

export interface Gallery4Item {
  id: string;
  title: string;
  description: string;
  href: string;
  image: string;
  badge?: string;
  badgeColor?: string;
}

export interface Gallery4Props {
  title?: string;
  description?: string;
  items: Gallery4Item[];
}

const Gallery4 = ({
  title = "Our Services",
  description = "Tools designed to accompany you through every part of your deen.",
  items,
}: Gallery4Props) => {
  const [carouselApi, setCarouselApi] = useState<CarouselApi>();
  const [canScrollPrev, setCanScrollPrev] = useState(false);
  const [canScrollNext, setCanScrollNext] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(0);

  useEffect(() => {
    if (!carouselApi) return;
    const updateSelection = () => {
      setCanScrollPrev(carouselApi.canScrollPrev());
      setCanScrollNext(carouselApi.canScrollNext());
      setCurrentSlide(carouselApi.selectedScrollSnap());
    };
    updateSelection();
    carouselApi.on("select", updateSelection);
    return () => { carouselApi.off("select", updateSelection); };
  }, [carouselApi]);

  return (
    <section id="services" className="py-20">
      <div className="container mx-auto px-6 md:px-12">
        <div className="mb-8 flex items-end justify-between md:mb-14">
          <div className="flex flex-col gap-3">
            <p className="text-xs font-bold uppercase tracking-widest text-[#10B981]">Services</p>
            <h2 className="text-3xl font-bold tracking-tight text-[#1E293B] md:text-4xl lg:text-5xl">
              {title}
            </h2>
            <p className="max-w-lg text-[#64748B]">{description}</p>
          </div>
          <div className="hidden shrink-0 gap-2 md:flex">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => carouselApi?.scrollPrev()}
              disabled={!canScrollPrev}
              className="disabled:pointer-events-auto text-[#1E293B] hover:bg-emerald-50 hover:text-[#10B981]"
            >
              <ArrowLeft className="size-5" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => carouselApi?.scrollNext()}
              disabled={!canScrollNext}
              className="disabled:pointer-events-auto text-[#1E293B] hover:bg-emerald-50 hover:text-[#10B981]"
            >
              <ArrowRight className="size-5" />
            </Button>
          </div>
        </div>
      </div>

      <div className="w-full">
        <Carousel
          setApi={setCarouselApi}
          opts={{ breakpoints: { "(max-width: 768px)": { dragFree: true } } }}
        >
          <CarouselContent className="ml-6 md:ml-12">
            {items.map((item) => (
              <CarouselItem key={item.id} className="max-w-[300px] pl-[20px] lg:max-w-[360px]">
                <a href={item.href} className="group rounded-xl block">
                  <div className="group relative h-full min-h-[27rem] max-w-full overflow-hidden rounded-2xl md:aspect-[5/4] lg:aspect-[16/9]">
                    <img
                      src={item.image}
                      alt={item.title}
                      className="absolute h-full w-full object-cover object-center transition-transform duration-300 group-hover:scale-105"
                    />
                    {/* Dark overlay: transparent top → black bottom */}
                    <div className="absolute inset-0 h-full bg-gradient-to-t from-black/90 via-black/50 to-transparent" />
                    <div className="absolute inset-x-0 bottom-0 flex flex-col items-start p-6 text-white md:p-8">
                      {item.badge && (
                        <span className={`mb-3 inline-block text-[11px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wide ${item.badgeColor ?? 'bg-[#10B981]/30 text-white'}`}>
                          {item.badge}
                        </span>
                      )}
                      <div className="mb-2 text-xl font-semibold">{item.title}</div>
                      <div className="mb-8 line-clamp-2 text-white/80 text-sm">{item.description}</div>
                      <div className="flex items-center text-sm font-semibold">
                        Learn more{" "}
                        <ArrowRight className="ml-2 size-4 transition-transform group-hover:translate-x-1" />
                      </div>
                    </div>
                  </div>
                </a>
              </CarouselItem>
            ))}
          </CarouselContent>
        </Carousel>

        <div className="mt-8 flex justify-center gap-2">
          {items.map((_, index) => (
            <button
              key={index}
              className={`h-2 w-2 rounded-full transition-colors ${currentSlide === index ? "bg-[#10B981]" : "bg-[#10B981]/20"}`}
              onClick={() => carouselApi?.scrollTo(index)}
              aria-label={`Go to slide ${index + 1}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
};

export { Gallery4 };
