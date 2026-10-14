import { useEffect, useRef, useState } from "react";
import type { ElementType, KeyboardEvent, MouseEvent } from "react";
import { ArrowRight } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface OrbitItem {
  id: number;
  title: string;
  content: string;
  icon: ElementType;
  /** In-page anchor the card's link jumps to, e.g. "#chat". */
  href: string;
}

interface RadialOrbitalTimelineProps {
  timelineData: OrbitItem[];
  className?: string;
}

const MAX_RADIUS = 200;
// Space kept between the orbit and the container edge for node labels.
const EDGE_PADDING = 56;
const GLOW_SIZE = 64;
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

export default function RadialOrbitalTimeline({
  timelineData,
  className,
}: RadialOrbitalTimelineProps) {
  const [activeNodeId, setActiveNodeId] = useState<number | null>(null);
  const [rotationAngle, setRotationAngle] = useState<number>(0);
  const [autoRotate, setAutoRotate] = useState<boolean>(true);
  const [radius, setRadius] = useState<number>(MAX_RADIUS);
  // Lazy initializer: read the OS setting once, on the first render.
  const [reduceMotion, setReduceMotion] = useState<boolean>(
    () => window.matchMedia(REDUCED_MOTION_QUERY).matches
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const orbitRef = useRef<HTMLDivElement>(null);

  // Shrink the orbit on narrow screens so nodes never leave the viewport.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      const fit = Math.min(width, height) / 2 - EDGE_PADDING;
      setRadius(Math.max(90, Math.min(MAX_RADIUS, fit)));
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Respect the OS "reduce motion" setting: no constant spinning.
  // The effect only listens for the user changing it while the page is open.
  useEffect(() => {
    const query = window.matchMedia(REDUCED_MOTION_QUERY);
    const onChange = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (!autoRotate || reduceMotion) return;
    const rotationTimer: ReturnType<typeof setInterval> = setInterval(() => {
      setRotationAngle((prev) => Number(((prev + 0.3) % 360).toFixed(3)));
    }, 50);
    return () => clearInterval(rotationTimer);
  }, [autoRotate, reduceMotion]);

  const resetView = () => {
    setActiveNodeId(null);
    setAutoRotate(true);
  };

  const handleContainerClick = (e: MouseEvent<HTMLDivElement>) => {
    if (e.target === containerRef.current || e.target === orbitRef.current) {
      resetView();
    }
  };

  // Rotate so the chosen node sits at the top of the orbit (270deg).
  const centerViewOnNode = (nodeId: number) => {
    const nodeIndex = timelineData.findIndex((item) => item.id === nodeId);
    if (nodeIndex === -1) return;
    setRotationAngle(270 - (nodeIndex / timelineData.length) * 360);
  };

  const toggleItem = (id: number) => {
    if (activeNodeId === id) {
      resetView();
      return;
    }
    setActiveNodeId(id);
    setAutoRotate(false);
    centerViewOnNode(id);
  };

  // Native <button>s already handle Enter and Space; only Escape is ours.
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") resetView();
  };

  const calculateNodePosition = (index: number, total: number) => {
    const angle = ((index / total) * 360 + rotationAngle) % 360;
    const radian = (angle * Math.PI) / 180;

    const x = radius * Math.cos(radian);
    const y = radius * Math.sin(radian);

    // Nodes "in front" (bottom of the orbit) are larger in z and brighter.
    const zIndex = Math.round(100 + 50 * Math.cos(radian));
    const opacity = Math.max(
      0.4,
      Math.min(1, 0.4 + 0.6 * ((1 + Math.sin(radian)) / 2))
    );

    return { x, y, zIndex, opacity };
  };

  return (
    <div
      className={cn(
        // isolate: node z-indexes (100-200) stay inside this component instead
        // of competing with the page's nav bar and dialogs.
        "isolate w-full h-screen flex flex-col items-center justify-center overflow-hidden",
        className
      )}
      ref={containerRef}
      onClick={handleContainerClick}
      onKeyDown={handleKeyDown}
    >
      <div className="relative w-full max-w-4xl h-full flex items-center justify-center">
        <div
          className="absolute w-full h-full flex items-center justify-center"
          ref={orbitRef}
          style={{ perspective: "1000px" }}
        >
          <div className="absolute w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 via-blue-500 to-teal-500 animate-pulse flex items-center justify-center z-10">
            <div className="absolute w-20 h-20 rounded-full border border-white/20 animate-ping opacity-70"></div>
            <div
              className="absolute w-24 h-24 rounded-full border border-white/10 animate-ping opacity-50"
              style={{ animationDelay: "0.5s" }}
            ></div>
            <div className="w-8 h-8 rounded-full bg-white/80 backdrop-blur-md"></div>
          </div>

          <div
            className="absolute rounded-full border border-white/10"
            style={{ width: radius * 2, height: radius * 2 }}
          ></div>

          {timelineData.map((item, index) => {
            const position = calculateNodePosition(index, timelineData.length);
            const isExpanded = activeNodeId === item.id;
            const Icon = item.icon;
            const cardId = `orbit-card-${item.id}`;

            const nodeStyle = {
              transform: `translate(${position.x}px, ${position.y}px)`,
              zIndex: isExpanded ? 200 : position.zIndex,
              opacity: isExpanded ? 1 : position.opacity,
            };

            // The card is a sibling of the node button, not inside it: a link
            // nested in a button is invalid HTML and confuses screen readers.
            return (
              <div key={item.id} className="absolute transition-all duration-700" style={nodeStyle}>
                <button
                  type="button"
                  aria-expanded={isExpanded}
                  aria-controls={isExpanded ? cardId : undefined}
                  className="relative block cursor-pointer rounded-full focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleItem(item.id);
                  }}
                >
                  <span
                    aria-hidden="true"
                    className="absolute rounded-full"
                    style={{
                      background: `radial-gradient(circle, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0) 70%)`,
                      width: `${GLOW_SIZE}px`,
                      height: `${GLOW_SIZE}px`,
                      left: `-${(GLOW_SIZE - 40) / 2}px`,
                      top: `-${(GLOW_SIZE - 40) / 2}px`,
                    }}
                  ></span>

                  <span
                    className={cn(
                      "relative w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300",
                      isExpanded
                        ? "bg-white text-black border-white shadow-lg shadow-white/30 scale-150"
                        : "bg-black text-white border-white/40"
                    )}
                  >
                    <Icon size={16} aria-hidden="true" />
                  </span>

                  <span
                    className={cn(
                      "absolute top-12 left-1/2 -translate-x-1/2 whitespace-nowrap text-xs font-semibold tracking-wider transition-all duration-300",
                      isExpanded ? "text-white scale-125" : "text-white/70"
                    )}
                  >
                    {item.title}
                  </span>
                </button>

                {isExpanded && (
                  <Card
                    id={cardId}
                    className="absolute top-20 left-1/2 -translate-x-1/2 w-64 bg-black/90 backdrop-blur-lg border border-white/30 text-white shadow-xl shadow-white/10 overflow-visible"
                  >
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-px h-3 bg-white/50"></div>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">{item.title}</CardTitle>
                    </CardHeader>
                    <CardContent className="text-xs text-white/80">
                      <p>{item.content}</p>
                      <a
                        href={item.href}
                        // No onClick that closes the card: removing the link from the
                        // page during the click can cancel the navigation.
                        className={cn(
                          buttonVariants({ size: "sm" }),
                          "mt-4 w-full gap-1.5"
                        )}
                      >
                        Go to section
                        <ArrowRight aria-hidden="true" />
                      </a>
                    </CardContent>
                  </Card>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
