#!/usr/bin/perl -wT
# Translate webpages to the dialect spoken in Berlin, Germany
use strict;
use URI; # for absolutizing urls
use CGI qw(-no_xhtml); # output HTML

# Clean up environment for taint mode before calling external applications
BEGIN {
    $ENV{PATH} = "/bin:/usr/bin";
    delete @ENV{ qw( IFS CDPATH ENV BASH_ENV ) };
}

# Security measures
$CGI::POST_MAX=1024*100;  # max 100 KBytes posts
$CGI::DISABLE_UPLOADS = 1;  # no uploads

# Globals
my $berlinified = undef; # String, where CGI-output is saved
# Adjust the following path to your server settings
my $new_query = "http://localhost/cgi-bin/berlinifyer.cgi?url=";
my $outfile = undef;
my $q = new CGI; # cgi object

if ($q->param()) {
    my $url = $q->param('url');
    unless ( ($url =~ m|^((?:[^:/?#]+:)?(?://[^/?#]*)?[^?#]*(?:\?[^#]*)?(?:#.*)?)| )  && (length($url) > 11) ) {
	slowdeath("Der eingegebene URL '$url' wird von diesem Programm nich akzeptiert!");
    }
    $url = $1; # untainted

    # Create parser object
    use HTML::Parser;
    my $p = HTML::Parser->new( api_version => 3,
			       start_h => [\&start, "self, tag, attr, attrseq, text"],
			       text_h => [ \&text, "self, dtext" ],
			       end_h   => [\&end, "self, tag, text"]
			       #comment_h => [""],
			       );
    # Event handlers for HTML parser
    sub start {
	my ($self, $tag, $attr, $attrseq, $origtext) = @_;
	# Expand relative to full urls. Prepend $new_query to
	# webpage links, i.e. <a href="...">, so that linked pages
	# will be berlinified as well.
	# Applet and Object tags are currently ignored.
	
	# don't berlinify the contents of style tags
	if ($tag eq 'style') {
	    $self->{lasttag} = 1;
	    $berlinified .= $origtext;
	    return;
	}

	# handle scripts
	if ($tag eq 'script') {
	    if ( defined($attr->{'src'}) ) { # external
		my $abs_url = URI->new_abs($attr->{'src'}, $p->{base});
		$attr->{'src'} =~ s|$attr->{'src'}|$abs_url|;
		$berlinified .= "<$tag ";
		for(@$attrseq) {
		    $berlinified .= $_ . qq(="$attr->{$_}" );
		}
		$berlinified .= ">";
	    } else { # internal
		$self->{lasttag} = 1;
		$berlinified .= $origtext;
		return;
	    }
	} 
	
	# handle external style sheets
	if ($tag eq 'link') {
	    if (defined($attr->{'href'})) {
		my $abs_url = URI->new_abs($attr->{'href'}, $p->{base});
		$attr->{'href'} =~ s|$attr->{'href'}|$abs_url|;
		$berlinified .= "<$tag ";
		for(@$attrseq) {
		    $berlinified .= $_ . qq(="$attr->{$_}" );
		}
		$berlinified .= ">";
		return;
	    }
	}
	
	# handle links, images 
	if ($tag eq 'a' || $tag eq 'img') {
	    if (defined($attr->{'href'})) {
		my $abs_url = URI->new_abs($attr->{'href'}, $p->{base});
		my $new_url = $new_query . $abs_url;
		$attr->{'href'} =~ s|$attr->{'href'}|$new_url|;
	    } elsif (defined($attr->{'src'})) {
		my $abs_url = URI->new_abs($attr->{'src'}, $p->{base});
		$attr->{'src'} =~ s|$attr->{'src'}|$abs_url|;
	    }
	    $berlinified .= "<$tag ";
	    for(@$attrseq) {
		$berlinified .= $_ . qq(="$attr->{$_}" );
	    }
	    $berlinified .= ">";
	    return;
	} # if ($tag eq 'a' || $tag eq 'img')
	
        # all other tags
	else {
	    $berlinified .= $origtext;
	    return;
	}
    } # sub start

    sub text {
	my ($self, $text) = @_;
	if (defined($self->{lasttag})) {
	    $berlinified .= $text;
	    return;
	}
	$text = substitute($text);
	$berlinified .= $text;
    }

    sub end {
	my ($self, $tag, $origtext) = @_;
	$berlinified .= $origtext;
	if ($tag =~ m/style|script/) {
	    $self->{lasttag} = undef;
	}
    }

    # Get document and base url
    use LWP;
    my $doc;
    my $ua = LWP::UserAgent->new();
    my $request = HTTP::Request->new(GET => $url);
    my $response = $ua->request($request);
    if ($response->is_success) {
	$p->{base} = $response->base();
	$doc = $response->content();
    } else { slowdeath("Das Dokument '$url' konnte nicht heruntergeladen werden!"); }
    
    # Parse HTML
    $p->parse($doc);
    $p->eof(); # Clear buffer

    print $q->header();
    print $berlinified;
} # if ($q->param())
else { # print HTML form
    my $title = 'Berlinifyer';
    print $q->header(),$q->start_html( {'title'=>$title,'author'=>'Ramiro G&oacute;mez'} );
    print $q->p('Hier k&ouml;nnen Web-Dokumente ins Berlinische �bersetzt werden. Bitte geben Sie die Internetadresse, des zu �bersetzenden HTML-Dokuments an.'),
    $q->start_form({'method'=>'get'}),$q->textfield({'name'=>'url',
				    'size'=>'50',
				    'maxlength'=>'100',
				    'default'=>'http://'}),$q->submit(),
    $q->end_form(),$q->end_html();
}

# "translate" to Berlin's dialect 
sub substitute {
    my $line = shift;
    my $vowel = 'aeiou���';
    #my $consonant = 'bcdfghjklmnpqrstvwxyz';
    my %subst_words = ('An der' => 'Anna',
		       'an der' => 'anna',
		       'An die' => 'Anne',
		       'an die' => 'anne',
		       'Auch' => 'Och',
		       'auch' => 'och',
		       'Bruder' => 'Atze',
		       'Br�der' => 'Atzen',
		       'Du' => 'De',
		       'du' => 'de',
		       'Frau' => 'Butze',
		       'Frauen' => 'Butzen',
		       'Freundin' => 'Ficke',
		       'Geld' => 'Patte',
		       'Gesellschaft' => 'Blase',
		       'Hitze' => 'Affenhitze',
		       'Ich' => 'Ick',
		       'ich' => 'ick',
		       'In der' => 'Inna',
		       'in der' => 'inna',
		       'In die' => 'Inne',
		       'in die' => 'inne',
		       'Kind' => 'Ableja',
		       'Kinder' => 'Ableja',
		       'Nein' => 'Nee',
		       'nein' => 'nee',
		       'Mutter' => 'Olle',
		       'Polizist' => 'Bulle',
		       'Polizisten' => 'Bullen',
		       'Rollstuhl' => 'AOK-Choppa',
		       'Rollst�hle' => 'AOK-Choppa',
		       'Schwester' => 'Atze',
		       'Schwestern' => 'Atzen',
		       'Streifenwagen' => 'Bullentaxe',
		       'Vater' => 'Oller',
		       'Verwandtschaft' => 'Blase',
		       'Was' => 'Wat',
		       'was' => 'wat');
	
    for(keys %subst_words) {$line =~ s/(\b)$_(\b)/$1$subst_words{$_}$2/g;}
    $line =~ s|(\b)Auf|$1Uff|g;
    $line =~ s|(\b)auf|$1uff|g;
    $line =~ s|(\w{2,})er([^$vowel])|$1a$2|gi;
    $line =~ s|([$vowel])r([^$vowel])|$1a$2|g;
    $line =~ s|([$vowel])hr(\b)|$1a$2|g;
    $line =~ s|([^n])g([r$vowel])|$1j$2|g;
    $line =~ s/([^$vowel][^n])g(\b)/$1ch$2/g;
    return $line;
}

# Handle incorrect input
sub slowdeath {
    my $message = shift;
    print $q->header(),
    $q->start_html(-title=>"Fehler"),
    $q->p($message), $q->end_html;
    exit(1);
}
__END__
#### Todo ####
Frames
Berlinisch Lexikon c-d
