import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'difficulty',
  standalone: true
})
export class DifficultyPipe implements PipeTransform {
  transform(value: string | null | undefined): string {
    if (!value) return 'Unknown';

    // Handle Deep Space
    if (value === 'DS') {
      return 'Deep Space';
    }

    // Handle T8+ (Profound)
    if (value === 'T8+') {
      return 'Timemark 8 (Profound)';
    }

    // Handle T16+ (Uber Profound)
    if (value === 'T16+') {
      return 'Timemark 16 (Uber Profound)';
    }

    // Handle T17+ (Apex Profound)
    if (value === 'T17+') {
      return 'Timemark 17 (Apex Profound)';
    }

    // Handle Uber variants
    if (value.startsWith('Uber')) {
      const tierMatch = value.match(/Uber(?:_)?(\d+)/);
      if (tierMatch) {
        return `Timemark ${tierMatch[1]} (Uber)`;
      }
      return value; // Fallback if no tier found
    }

    // Handle standard Timemark format (T8_2, T8_1, T8_0, etc.)
    const underscoreMatch = value.match(/T(\d+)_(\d+)/);
    if (underscoreMatch) {
      const tier = underscoreMatch[1];
      const level = underscoreMatch[2];
      return `Timemark ${tier}.${level}`;
    }

    // Handle simple Timemark format (T8, T7, T6, etc.)
    const simpleMatch = value.match(/T(\d+)/);
    if (simpleMatch) {
      return `Timemark ${simpleMatch[1]}`;
    }

    // Fallback: return original value
    return value;
  }
}
