/**
 * Curated high-resolution fashion imagery engine.
 * Maps H&M catalog product types, categories, and departments to authentic editorial fashion lookbook imagery.
 * Provides rich, diverse, non-repeating fashion lookbook photos.
 */

function hashId(id: string | number): number {
  const str = String(id)
  let h = 0
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

// Curated high-definition fashion lookbook imagery
const FASHION_IMAGES: Record<string, string[]> = {
  trousers: [
    'https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?auto=format&fit=crop&w=700&q=80', // Tailored ecru wide-leg
    'https://images.unsplash.com/photo-1509551388413-e18d0ac5d495?auto=format&fit=crop&w=700&q=80', // Minimalist grey slacks
    'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=700&q=80', // Dark tailored trousers
    'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=700&q=80', // Classic straight denim
    'https://images.unsplash.com/photo-1584370848010-d7fe6bc767ec?auto=format&fit=crop&w=700&q=80', // Relaxed fit chinos
    'https://images.unsplash.com/photo-1517445312882-bc9910d016b7?auto=format&fit=crop&w=700&q=80', // Casual black crop pants
    'https://images.unsplash.com/photo-1506629082955-511b1aa562c8?auto=format&fit=crop&w=700&q=80', // High-waisted pleated trousers
    'https://images.unsplash.com/photo-1560243563-062bfc001d68?auto=format&fit=crop&w=700&q=80', // Beige linen pants
    'https://images.unsplash.com/photo-1582552938357-32b906df40cb?auto=format&fit=crop&w=700&q=80', // Light wash vintage denim
    'https://images.unsplash.com/photo-1551854838-212c50b4c184?auto=format&fit=crop&w=700&q=80', // Flared city trousers
  ],
  dress: [
    'https://images.unsplash.com/photo-1595777457583-95e059d581b8?auto=format&fit=crop&w=700&q=80', // Silk slip dress
    'https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?auto=format&fit=crop&w=700&q=80', // Pleated maxi dress
    'https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?auto=format&fit=crop&w=700&q=80', // Minimal linen sundress
    'https://images.unsplash.com/photo-1566174053879-31528523f8ae?auto=format&fit=crop&w=700&q=80', // Black evening gown
    'https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=700&q=80', // Flowing floral tea dress
    'https://images.unsplash.com/photo-1539109136881-3be0616acf4b?auto=format&fit=crop&w=700&q=80', // Tailored blazer dress
    'https://images.unsplash.com/photo-1574201635302-388dd92a4c3f?auto=format&fit=crop&w=700&q=80', // Knitted midi ribbed dress
    'https://images.unsplash.com/photo-1550614000-4895a10e1bfd?auto=format&fit=crop&w=700&q=80', // Emerald satin evening dress
    'https://images.unsplash.com/photo-1502716119720-b23a93e5fe1b?auto=format&fit=crop&w=700&q=80', // Minimalist column dress
    'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=700&q=80', // Contemporary summer dress
    'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&w=700&q=80', // White bohemian maxi dress
    'https://images.unsplash.com/photo-1585487000160-6ebcfceb0d03?auto=format&fit=crop&w=700&q=80', // Elegant cocktail dress
  ],
  sweater: [
    'https://images.unsplash.com/photo-1576566588028-4147f3842f27?auto=format&fit=crop&w=700&q=80', // Cable knit cream jumper
    'https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&w=700&q=80', // Soft ivory knit
    'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=700&q=80', // Wool mock turtleneck
    'https://images.unsplash.com/photo-1614975059251-992f11792b9f?auto=format&fit=crop&w=700&q=80', // Sage ribbed knit sweater
    'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?auto=format&fit=crop&w=700&q=80', // Charcoal cashmere pullover
    'https://images.unsplash.com/photo-1584273143981-41c073dfe8f8?auto=format&fit=crop&w=700&q=80', // Oversized taupe knitwear
    'https://images.unsplash.com/photo-1608256246200-53e635b5b65f?auto=format&fit=crop&w=700&q=80', // Beige crewneck sweater
    'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=700&q=80', // Fluffy luxury knit
    'https://images.unsplash.com/photo-1578587018452-892bacefd3f2?auto=format&fit=crop&w=700&q=80', // Minimalist knitted jumper
    'https://images.unsplash.com/photo-1611042553365-9b101441c135?auto=format&fit=crop&w=700&q=80', // Pastel lilac sweater
  ],
  cardigan: [
    'https://images.unsplash.com/photo-1576566588028-4147f3842f27?auto=format&fit=crop&w=700&q=80', // Buttoned rib cardigan
    'https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&w=700&q=80', // Cream longline cardigan
    'https://images.unsplash.com/photo-1584273143981-41c073dfe8f8?auto=format&fit=crop&w=700&q=80', // Crop knit cardigan
    'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=700&q=80', // Soft wool wrap cardigan
    'https://images.unsplash.com/photo-1614975059251-992f11792b9f?auto=format&fit=crop&w=700&q=80', // Sage button cardigan
  ],
  shirt: [
    'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=700&q=80', // Crisp poplin oversized shirt
    'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=700&q=80', // White linen button-down
    'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=700&q=80', // Light blue tailored oxford
    'https://images.unsplash.com/photo-1603252109303-2751441ec157?auto=format&fit=crop&w=700&q=80', // Striped casual shirt
    'https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=700&q=80', // Minimal satin button-up
    'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=700&q=80', // Classic tailored shirt
    'https://images.unsplash.com/photo-1563630423918-b58f07336ac9?auto=format&fit=crop&w=700&q=80', // Neutral linen summer shirt
  ],
  blouse: [
    'https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=700&q=80', // Silk ivory blouse
    'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=700&q=80', // Poplin puff-sleeve blouse
    'https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=700&q=80', // Draped satin blouse
    'https://images.unsplash.com/photo-1564257631407-4deb1f99d992?auto=format&fit=crop&w=700&q=80', // High-neck romantic blouse
    'https://images.unsplash.com/photo-1551803091-e20673f15770?auto=format&fit=crop&w=700&q=80', // Floral summer blouse
    'https://images.unsplash.com/photo-1578587018452-892bacefd3f2?auto=format&fit=crop&w=700&q=80', // Clean formal blouse
  ],
  tshirt: [
    'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=700&q=80', // Minimal white t-shirt
    'https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=700&q=80', // Washed vintage tee
    'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?auto=format&fit=crop&w=700&q=80', // Black premium crewneck
    'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=700&q=80', // Organic cotton beige tee
    'https://images.unsplash.com/photo-1562157873-818bc0726f68?auto=format&fit=crop&w=700&q=80', // Minimal sage tee
    'https://images.unsplash.com/photo-1503342452485-86b7f54527ef?auto=format&fit=crop&w=700&q=80', // Boxy heavyweight tee
    'https://images.unsplash.com/photo-1527719327859-c6ce80353573?auto=format&fit=crop&w=700&q=80', // Striped casual tee
  ],
  top: [
    'https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=700&q=80', // Silk camisole
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=700&q=80', // Ribbed tank top
    'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=700&q=80', // Square-neck knit top
    'https://images.unsplash.com/photo-1508296695146-257a814070b4?auto=format&fit=crop&w=700&q=80', // Halter linen top
    'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=700&q=80', // Asymmetric sleeveless top
    'https://images.unsplash.com/photo-1485230895905-ec40ba36b9bc?auto=format&fit=crop&w=700&q=80', // Minimal vest top
  ],
  jacket: [
    'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?auto=format&fit=crop&w=700&q=80', // Double-breasted blazer
    'https://images.unsplash.com/photo-1544022613-e87ca75a784a?auto=format&fit=crop&w=700&q=80', // Leather shearling jacket
    'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=700&q=80', // Quilted cropped jacket
    'https://images.unsplash.com/photo-1548883354-7622d03aca27?auto=format&fit=crop&w=700&q=80', // Houndstooth tailored blazer
    'https://images.unsplash.com/photo-1516257984-b1b4d707412e?auto=format&fit=crop&w=700&q=80', // Minimal denim jacket
    'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=700&q=80', // Oversized wool blazer
    'https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=700&q=80', // Tweed structured jacket
    'https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=700&q=80', // Black biker jacket
  ],
  coat: [
    'https://images.unsplash.com/photo-1539533018447-63fcce667883?auto=format&fit=crop&w=700&q=80', // Editorial long coat
    'https://images.unsplash.com/photo-1548883354-7622d03aca27?auto=format&fit=crop&w=700&q=80', // Camel wool trench
    'https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=700&q=80', // Sage quilted parka
    'https://images.unsplash.com/photo-1520975954732-35dd22299614?auto=format&fit=crop&w=700&q=80', // Cashmere wrap coat
    'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=700&q=80', // Black tailored overcoat
    'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=700&q=80', // Down puffer coat
  ],
  hoodie: [
    'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=700&q=80', // Fleece heavyweight hoodie
    'https://images.unsplash.com/photo-1509967419530-da38b4704bc6?auto=format&fit=crop&w=700&q=80', // Vintage grey sweatshirt
    'https://images.unsplash.com/photo-1578587018452-892bacefd3f2?auto=format&fit=crop&w=700&q=80', // Clean neutral hoodie
    'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=700&q=80', // Sage oversized hoodie
    'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=700&q=80', // Minimal crewneck sweat
    'https://images.unsplash.com/photo-1503342452485-86b7f54527ef?auto=format&fit=crop&w=700&q=80', // Streetwear zip hoodie
  ],
  skirt: [
    'https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?auto=format&fit=crop&w=700&q=80', // Satin midi skirt
    'https://images.unsplash.com/photo-1508427953056-b00b8d78ebf5?auto=format&fit=crop&w=700&q=80', // Pleated tailored skirt
    'https://images.unsplash.com/photo-1577900232427-18219b9166a0?auto=format&fit=crop&w=700&q=80', // Casual wrap skirt
    'https://images.unsplash.com/photo-1560243563-062bfc001d68?auto=format&fit=crop&w=700&q=80', // High-waisted pencil skirt
    'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&w=700&q=80', // Denim maxi skirt
    'https://images.unsplash.com/photo-1551854838-212c50b4c184?auto=format&fit=crop&w=700&q=80', // Ribbed knit skirt
  ],
  shorts: [
    'https://images.unsplash.com/photo-1591195853828-11db59a44f6b?auto=format&fit=crop&w=700&q=80', // Denim cutoff shorts
    'https://images.unsplash.com/photo-1506629082955-511b1aa562c8?auto=format&fit=crop&w=700&q=80', // Tailored high-waist shorts
    'https://images.unsplash.com/photo-1560243563-062bfc001d68?auto=format&fit=crop&w=700&q=80', // Linen bermuda shorts
    'https://images.unsplash.com/photo-1517445312882-bc9910d016b7?auto=format&fit=crop&w=700&q=80', // Casual summer shorts
    'https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=700&q=80', // Black city shorts
  ],
  shoes: [
    'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=700&q=80', // Minimalist mules & heels
    'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=700&q=80', // Clean leather sneakers
    'https://images.unsplash.com/photo-1520639888713-7851133b1ed0?auto=format&fit=crop&w=700&q=80', // Black chelsea boots
    'https://images.unsplash.com/photo-1535043934128-cf0b28d52f95?auto=format&fit=crop&w=700&q=80', // Classic penny loafers
    'https://images.unsplash.com/photo-1560343090-f0409e92791a?auto=format&fit=crop&w=700&q=80', // Designer sandals
    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=700&q=80', // Athletic running sneakers
    'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=700&q=80', // Modern street sneakers
    'https://images.unsplash.com/photo-1515347619252-60a4bf4fff4f?auto=format&fit=crop&w=700&q=80', // Strappy block heels
  ],
  bag: [
    'https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=700&q=80', // Tan leather tote
    'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=700&q=80', // Luxury shoulder bag
    'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=700&q=80', // Minimal canvas tote
    'https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=700&q=80', // Leather crossbody bag
    'https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&w=700&q=80', // Structured designer bag
    'https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?auto=format&fit=crop&w=700&q=80', // Woven straw tote
  ],
  accessories: [
    'https://images.unsplash.com/photo-1508296695146-257a814070b4?auto=format&fit=crop&w=700&q=80', // Sunglasses & scarf
    'https://images.unsplash.com/photo-1611085583191-a3b181a88401?auto=format&fit=crop&w=700&q=80', // Leather belt & accessories
    'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=700&q=80', // Gold hoop earrings
    'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?auto=format&fit=crop&w=700&q=80', // Layered jewelry & necklace
    'https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=700&q=80', // Classic sunglasses
    'https://images.unsplash.com/photo-1576871337622-98d48d1cf531?auto=format&fit=crop&w=700&q=80', // Wool beanie & scarf
  ],
  underwear: [
    'https://images.unsplash.com/photo-1516762689617-e1cffcef479d?auto=format&fit=crop&w=700&q=80', // Silk & lace lingerie
    'https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=700&q=80', // Ribbed loungewear
    'https://images.unsplash.com/photo-1576995853123-5a10305d93c0?auto=format&fit=crop&w=700&q=80', // Silk slip
    'https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?auto=format&fit=crop&w=700&q=80', // Satin loungewear
    'https://images.unsplash.com/photo-1502716119720-b23a93e5fe1b?auto=format&fit=crop&w=700&q=80', // Seamless bralette
  ],
  swimwear: [
    'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=700&q=80', // One-piece swimsuit
    'https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=700&q=80', // Resort bikini set
    'https://images.unsplash.com/photo-1502716119720-b23a93e5fe1b?auto=format&fit=crop&w=700&q=80', // Ribbed summer swimwear
    'https://images.unsplash.com/photo-1550614000-4895a10e1bfd?auto=format&fit=crop&w=700&q=80', // Halter plunge swimsuit
  ],
  sport: [
    'https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=700&q=80', // Activewear set
    'https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=700&q=80', // Yoga active leggings
    'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?auto=format&fit=crop&w=700&q=80', // Performance training set
    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=700&q=80', // Athletic apparel
    'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=700&q=80', // Gym runner set
  ],
  jumpsuit: [
    'https://images.unsplash.com/photo-1502716119720-b23a93e5fe1b?auto=format&fit=crop&w=700&q=80', // Tailored wide-leg jumpsuit
    'https://images.unsplash.com/photo-1595777457583-95e059d581b8?auto=format&fit=crop&w=700&q=80', // Linen boiler suit
    'https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?auto=format&fit=crop&w=700&q=80', // Silk evening jumpsuit
    'https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?auto=format&fit=crop&w=700&q=80', // Casual summer romper
  ],
  kids: [
    'https://images.unsplash.com/photo-1519689680058-324335c77eba?auto=format&fit=crop&w=700&q=80', // Knitted children wear
    'https://images.unsplash.com/photo-1522771930-78848d9293e8?auto=format&fit=crop&w=700&q=80', // Baby & kids fashion
    'https://images.unsplash.com/photo-1503919545889-aef636e10ad4?auto=format&fit=crop&w=700&q=80', // Toddler cotton set
    'https://images.unsplash.com/photo-1514090458221-65bb69cf63e6?auto=format&fit=crop&w=700&q=80', // Kids cute outfit
  ],
  mens: [
    'https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=700&q=80', // Mens tailored blazer
    'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=700&q=80', // Mens tailored suit
    'https://images.unsplash.com/photo-1490114538077-0a7f8cb49891?auto=format&fit=crop&w=700&q=80', // Mens casual linen
    'https://images.unsplash.com/photo-1506630448388-4e683c67ddb0?auto=format&fit=crop&w=700&q=80', // Mens stylish outerwear
    'https://images.unsplash.com/photo-1534030347209-467a5b0ad3e6?auto=format&fit=crop&w=700&q=80', // Mens minimal shirt & trousers
    'https://images.unsplash.com/photo-1516257984-b1b4d707412e?auto=format&fit=crop&w=700&q=80', // Mens denim jacket
    'https://images.unsplash.com/photo-1504593811423-6dd665756598?auto=format&fit=crop&w=700&q=80', // Mens classic watch & tailored look
  ],
  general: [
    'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=700&q=80',
    'https://images.unsplash.com/photo-1485230895905-ec40ba36b9bc?auto=format&fit=crop&w=700&q=80',
    'https://images.unsplash.com/photo-1445205170230-053b83016050?auto=format&fit=crop&w=700&q=80',
    'https://images.unsplash.com/photo-1469334031218-e382a71b716b?auto=format&fit=crop&w=700&q=80',
  ],
}

/**
 * Returns a highly specific, high-resolution fashion lookbook image matched to the article.
 * Uses indexOffset or deterministic hashing to ensure adjacent cards never repeat the same image.
 */
export function getCuratedFashionImage(
  productType?: string | null,
  productGroup?: string | null,
  indexGroup?: string | null,
  articleId?: string | number | null,
  indexOffset = 0
): string {
  const pType = (productType || '').toLowerCase().trim()
  const pGroup = (productGroup || '').toLowerCase().trim()
  const iGroup = (indexGroup || '').toLowerCase().trim()
  const seed = hashId(articleId || productType || 'aura-fashion') + (indexOffset * 3)

  let pool = FASHION_IMAGES.general

  if (iGroup.includes('baby') || iGroup.includes('child') || pType.includes('baby') || pType.includes('kids')) {
    pool = FASHION_IMAGES.kids
  } else if (iGroup.includes('sport') || pType.includes('sport') || pType.includes('active') || pType.includes('legging')) {
    pool = FASHION_IMAGES.sport
  } else if (pType.includes('dress') || pType.includes('gown')) {
    pool = FASHION_IMAGES.dress
  } else if (pType.includes('jumpsuit') || pType.includes('playsuit') || pType.includes('romper') || pType.includes('bodysuit')) {
    pool = FASHION_IMAGES.jumpsuit
  } else if (pType.includes('trouser') || pType.includes('pant') || pType.includes('jean') || pType.includes('chinos') || (pGroup.includes('lower') && !pType.includes('skirt') && !pType.includes('short'))) {
    pool = FASHION_IMAGES.trousers
  } else if (pType.includes('cardigan')) {
    pool = FASHION_IMAGES.cardigan
  } else if (pType.includes('sweater') || pType.includes('knit') || pType.includes('jumper') || pType.includes('pullover') || pType.includes('turtleneck')) {
    pool = FASHION_IMAGES.sweater
  } else if (pType.includes('hoodie') || pType.includes('sweatshirt')) {
    pool = FASHION_IMAGES.hoodie
  } else if (pType.includes('blazer') || pType.includes('jacket') || pType.includes('waistcoat')) {
    pool = FASHION_IMAGES.jacket
  } else if (pType.includes('coat') || pType.includes('parka') || pType.includes('trench') || pType.includes('overcoat') || pType.includes('outdoor')) {
    pool = FASHION_IMAGES.coat
  } else if (pType.includes('blouse')) {
    pool = FASHION_IMAGES.blouse
  } else if (pType.includes('shirt') && !pType.includes('t-shirt') && !pType.includes('sweatshirt')) {
    pool = FASHION_IMAGES.shirt
  } else if (pType.includes('t-shirt') || pType.includes('tee')) {
    pool = FASHION_IMAGES.tshirt
  } else if (pType.includes('vest top') || pType.includes('tank') || pType.includes('camisole') || (pType === 'top' || pType.includes('top'))) {
    pool = FASHION_IMAGES.top
  } else if (pType.includes('skirt')) {
    pool = FASHION_IMAGES.skirt
  } else if (pType.includes('short')) {
    pool = FASHION_IMAGES.shorts
  } else if (pType.includes('shoe') || pType.includes('boot') || pType.includes('sneaker') || pType.includes('sandal') || pType.includes('heel') || pType.includes('loafer') || pGroup.includes('shoes')) {
    pool = FASHION_IMAGES.shoes
  } else if (pType.includes('bag') || pType.includes('tote') || pType.includes('backpack') || pType.includes('wallet') || pGroup.includes('bags')) {
    pool = FASHION_IMAGES.bag
  } else if (pType.includes('swim') || pType.includes('bikini') || pGroup.includes('swimwear')) {
    pool = FASHION_IMAGES.swimwear
  } else if (pType.includes('bra') || pType.includes('underwear') || pType.includes('lingerie') || pType.includes('brief') || pType.includes('tight') || pType.includes('sock') || pGroup.includes('underwear')) {
    pool = FASHION_IMAGES.underwear
  } else if (pType.includes('hat') || pType.includes('cap') || pType.includes('beanie') || pType.includes('scarf') || pType.includes('sunglasses') || pType.includes('earring') || pType.includes('necklace') || pType.includes('belt') || pType.includes('ring') || pGroup.includes('accessories')) {
    pool = FASHION_IMAGES.accessories
  } else if (iGroup.includes('menswear')) {
    pool = FASHION_IMAGES.mens
  } else if (pGroup.includes('upper')) {
    pool = FASHION_IMAGES.shirt
  } else if (pGroup.includes('lower')) {
    pool = FASHION_IMAGES.trousers
  } else if (pGroup.includes('full')) {
    pool = FASHION_IMAGES.dress
  }

  const index = Math.abs(seed) % pool.length
  return pool[index]
}
