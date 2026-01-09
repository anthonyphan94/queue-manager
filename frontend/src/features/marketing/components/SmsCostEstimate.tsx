/**
 * SmsCostEstimate - Real-time SMS cost estimation display
 * 
 * TWILIO SMS PRICING BREAKDOWN (USA, as of Jan 2025):
 * 
 * 1. BASE RATE (Twilio fee per segment):
 *    - Long code / Toll-free / Short code: $0.0079 per segment
 *    - Source: https://www.twilio.com/en-us/sms/pricing/us
 * 
 * 2. CARRIER FEES (A2P 10DLC, per segment, passed through):
 *    - AT&T: $0.002/segment (registered)
 *    - T-Mobile: $0.003/segment (registered)
 *    - Verizon: $0.0025/segment
 *    - US Cellular: ~$0.002/segment
 *    - AVERAGE: ~$0.0025-$0.003/segment
 * 
 * 3. TOTAL ESTIMATED COST:
 *    Base ($0.0079) + Avg Carrier Fee ($0.003) = ~$0.0109/segment
 *    Rounded to $0.011 for display purposes
 * 
 * NOTE: This is an ESTIMATE. Actual costs may vary based on:
 * - Carrier mix of recipients
 * - A2P 10DLC registration status
 * - Volume tier discounts
 * - Monthly campaign fees are NOT included
 * 
 * Segment rules:
 * - GSM-7 (standard ASCII): 160 chars single, 153 chars per segment when concatenated
 * - UCS-2 (emojis, special chars): 70 chars single, 67 chars per segment when concatenated
 */

// Twilio SMS pricing breakdown
const TWILIO_BASE_RATE = 0.0079;     // Twilio's base rate per segment
const AVG_CARRIER_FEE = 0.003;       // Average A2P 10DLC carrier fee
const COST_PER_SEGMENT = TWILIO_BASE_RATE + AVG_CARRIER_FEE; // ~$0.0109

// GSM-7 character set (standard SMS encoding)
const GSM_7_CHARS = new Set(
    '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ !"#¤%&\'()*+,-./0123456789:;<=>?' +
    '¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà'
);

// Extended GSM-7 characters (count as 2 characters)
const GSM_7_EXTENDED = new Set('|^€{}[]~\\');

interface SmsCostEstimateProps {
    message: string;
    recipientCount?: number;
}

/**
 * Check if a message can be encoded as GSM-7
 */
function isGsm7Encodable(message: string): boolean {
    for (const char of message) {
        if (!GSM_7_CHARS.has(char) && !GSM_7_EXTENDED.has(char)) {
            return false;
        }
    }
    return true;
}

/**
 * Calculate the character count for GSM-7 encoding
 * Extended characters count as 2
 */
function getGsm7CharCount(message: string): number {
    let count = 0;
    for (const char of message) {
        count += GSM_7_EXTENDED.has(char) ? 2 : 1;
    }
    return count;
}

/**
 * Calculate the number of SMS segments for a message
 */
function calculateSegments(message: string): { segments: number; encoding: 'GSM-7' | 'UCS-2'; charCount: number } {
    if (!message || message.length === 0) {
        return { segments: 0, encoding: 'GSM-7', charCount: 0 };
    }

    const useGsm7 = isGsm7Encodable(message);

    if (useGsm7) {
        const charCount = getGsm7CharCount(message);
        // Single segment: 160 chars, Multi-segment: 153 chars each (7 chars for UDH header)
        const segments = charCount <= 160 ? 1 : Math.ceil(charCount / 153);
        return { segments, encoding: 'GSM-7', charCount };
    } else {
        const charCount = message.length;
        // Single segment: 70 chars, Multi-segment: 67 chars each (3 chars for UDH header)
        const segments = charCount <= 70 ? 1 : Math.ceil(charCount / 67);
        return { segments, encoding: 'UCS-2', charCount };
    }
}

/**
 * Format currency for display
 */
function formatCost(amount: number): string {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(amount);
}

export function SmsCostEstimate({ message, recipientCount = 1 }: SmsCostEstimateProps) {
    const { segments, encoding, charCount } = calculateSegments(message);

    // Don't show anything if no message
    if (!message.trim()) {
        return null;
    }

    const costPerMessage = segments * COST_PER_SEGMENT;
    const totalSegments = segments * recipientCount;
    const totalCost = costPerMessage * recipientCount;

    // Determine segment limit for display
    const singleLimit = encoding === 'GSM-7' ? 160 : 70;
    const multiLimit = encoding === 'GSM-7' ? 153 : 67;
    const effectiveLimit = segments === 1 ? singleLimit : multiLimit;

    return (
        <div className="sms-cost-estimate">
            <span className="cost-icon">💰</span>
            <div className="cost-details">
                {recipientCount === 1 ? (
                    // Single SMS display
                    <>
                        <span className="segment-info">
                            {segments} segment{segments !== 1 ? 's' : ''}
                            {encoding === 'UCS-2' && <span className="encoding-badge">Unicode</span>}
                        </span>
                        <span className="cost-divider">•</span>
                        <span className="cost-amount">
                            Estimated cost: <strong>~{formatCost(costPerMessage)}</strong>
                        </span>
                    </>
                ) : (
                    // Bulk CSV display
                    <>
                        <span className="segment-info">
                            {segments} segment{segments !== 1 ? 's' : ''}/msg × {recipientCount} recipient{recipientCount !== 1 ? 's' : ''} = {totalSegments} total
                            {encoding === 'UCS-2' && <span className="encoding-badge">Unicode</span>}
                        </span>
                        <span className="cost-divider">•</span>
                        <span className="cost-amount">
                            Estimated cost: <strong>~{formatCost(totalCost)}</strong>
                        </span>
                    </>
                )}
            </div>
        </div>
    );
}
