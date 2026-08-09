//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1;
function t() {
	e = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
t();
//#endregion
//#region node_modules/svelte/src/constants.js
var n = {}, r = Symbol("uninitialized"), i = "http://www.w3.org/1999/xhtml", a = Array.isArray, o = Array.prototype.indexOf, s = Array.prototype.includes, c = Array.from, l = Object.keys, u = Object.defineProperty, d = Object.getOwnPropertyDescriptor, f = Object.getOwnPropertyDescriptors, p = Object.prototype, m = Array.prototype, h = Object.getPrototypeOf, g = Object.isExtensible, _ = () => {};
function v(e) {
	return e();
}
function y(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function b() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var x = 1024, S = 2048, C = 4096, w = 8192, ee = 16384, te = 32768, ne = 1 << 25, re = 65536, ie = 1 << 19, ae = 1 << 20, oe = 1 << 25, se = 65536, ce = 1 << 21, le = 1 << 22, ue = 1 << 23, de = Symbol("$state"), fe = Symbol("legacy props"), pe = Symbol(""), me = Symbol("attributes"), he = Symbol("class"), ge = Symbol("style"), _e = Symbol("text"), ve = Symbol("form reset"), ye = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), be = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function xe(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function Se() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Ce(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function we(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Te() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Ee(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function De() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Oe() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function ke(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ae() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function je() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Me() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Ne() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Pe() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Fe(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Ie() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var T = !1;
function Le(e) {
	T = e;
}
var E;
function D(e) {
	if (e === null) throw Fe(), n;
	return E = e;
}
function Re() {
	return D(/* @__PURE__ */ I(E));
}
function O(e) {
	if (T) {
		if (/* @__PURE__ */ I(E) !== null) throw Fe(), n;
		E = e;
	}
}
function ze(e = 1) {
	if (T) {
		for (var t = e, n = E; t--;) n = /* @__PURE__ */ I(n);
		E = n;
	}
}
function Be(e = !0) {
	for (var t = 0, n = E;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ I(n);
		e && n.remove(), n = i;
	}
}
function Ve(e) {
	if (!e || e.nodeType !== 8) throw Fe(), n;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function He(e) {
	return e === this.v;
}
function Ue(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function We(e) {
	return !Ue(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var k = null;
function Ge(e) {
	k = e;
}
function Ke(t, n = !1, r) {
	k = {
		p: k,
		i: !1,
		c: null,
		e: null,
		s: t,
		x: null,
		r: G,
		l: e && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function qe(e) {
	var t = k, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) yn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, k = t.p, e ?? {};
}
function Je() {
	return !e || k !== null && k.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Ye = [];
function Xe() {
	var e = Ye;
	Ye = [], y(e);
}
function Ze(e) {
	if (Ye.length === 0 && !jt) {
		var t = Ye;
		queueMicrotask(() => {
			t === Ye && Xe();
		});
	}
	Ye.push(e);
}
function Qe() {
	for (; Ye.length > 0;) Xe();
}
function $e(e) {
	var t = G;
	if (t === null) return H.f |= ue, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	et(e, t);
}
function et(e, t) {
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var tt = ~(S | C | x);
function A(e, t) {
	e.f = e.f & tt | t;
}
function nt(e) {
	e.f & 512 || e.deps === null ? A(e, x) : A(e, C);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function rt(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= se, rt(t.deps));
}
function it(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), rt(e.deps), A(e, x);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var at = !1;
function ot(e) {
	var t = at;
	try {
		return at = !1, [e(), at];
	} finally {
		at = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var st = !1;
function ct() {
	st || (st = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ve]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function lt(e) {
	var t = H, n = G;
	W(null), Hn(null);
	try {
		return e();
	} finally {
		W(t), Hn(n);
	}
}
function ut(e, t, n, r = n) {
	e.addEventListener(t, () => lt(n));
	let i = e[ve];
	e[ve] = i ? () => {
		i(), r(!0);
	} : () => r(!0), ct();
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function dt(e) {
	let t = 0, n = Jt(0), r;
	return () => {
		gn() && (Y(n), Tn(() => (t === 0 && (r = X(() => e(() => $t(n)))), t += 1, () => {
			Ze(() => {
				--t, t === 0 && (r?.(), r = void 0, $t(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var ft = re | ie;
function pt(e, t, n, r) {
	new mt(e, t, n, r);
}
var mt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = T ? E : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = dt(() => (this.#m = Jt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Dn(() => {
			if (T) {
				let e = this.#t;
				Re();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#y() : this.#g();
			} else this.#b();
		}, ft), T && (this.#e = E);
	}
	#g() {
		try {
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#v(e);
		Ze(r), t && (this.#s = B(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#v(e) {
		var t = !1, n = !1;
		let r = () => {
			if (t) {
				Ie();
				return;
			}
			t = !0, n && Ne(), this.#s !== null && Nn(this.#s, () => {
				this.#s = null;
			}), this.#S(() => {
				this.#b();
			});
		};
		return {
			reset: r,
			invoke_onerror: () => {
				try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					et(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), Ze(() => {
			var e = this.#c = document.createDocumentFragment(), t = F();
			e.append(t), this.#a = this.#S(() => B(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Nn(this.#o, () => {
				this.#o = null;
			}), this.#x(j));
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Ln(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#x(j);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		it(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = G, n = H, r = k;
		Hn(this.#i), W(this.#i), Ge(this.#i.ctx);
		try {
			return Lt.ensure(), e();
		} catch (e) {
			return $e(e), null;
		} finally {
			Hn(t), W(n), Ge(r);
		}
	}
	#C(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#C(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#x(t), this.#o && Nn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Ze(() => {
			this.#d = !1, this.#m && Zt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Y(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		j?.is_fork ? (this.#a && j.skip_effect(this.#a), this.#o && j.skip_effect(this.#o), this.#s && j.skip_effect(this.#s), j.oncommit(() => {
			this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), T && (D(this.#t), ze(), D(Be()));
		let t = this.#n.failed, n = (e) => {
			let { reset: n, invoke_onerror: r } = this.#v(e);
			r(), t && (this.#s = this.#S(() => {
				try {
					return B(() => {
						var r = G;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return et(e, this.#i.parent), null;
				}
			}));
		};
		Ze(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				et(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => et(e, this.#i && this.#i.parent)) : n(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function ht(e, t, n, r) {
	let i = Je() ? yt : St;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = gt(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				et(e, s);
			}
			_t();
		}
	}
	var d = vt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ xt(e))).then(u).catch((e) => et(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), _t();
	}) : f();
}
function gt() {
	var e = G, t = H, n = k, r = j;
	return function(i = !0) {
		Hn(e), W(t), Ge(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function _t(e = !0) {
	Hn(null), W(null), Ge(null), e && j?.deactivate();
}
function vt() {
	var e = G, t = e.b, n = j, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function yt(e) {
	var t = 2 | S;
	return G !== null && (G.f |= ie), {
		ctx: k,
		deps: null,
		effects: null,
		equals: He,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: r,
		wv: 0,
		parent: G,
		ac: null
	};
}
var bt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function xt(e, t, n) {
	let i = G;
	i === null && Se();
	var a = void 0, o = Jt(r), s = !H, c = /* @__PURE__ */ new Set();
	return wn(() => {
		var t = G, n = b();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== ye && n.reject(e);
			}).finally(_t);
		} catch (e) {
			n.reject(e), _t();
		}
		var r = j;
		if (s) {
			if (t.f & 32768) var l = vt();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(bt);
			else for (let e of c.values()) e.reject(bt);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== bt && (r.activate(), t ? (o.f |= ue, Zt(o, t)) : (o.f & 8388608 && (o.f ^= ue), Zt(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), _n(() => {
		for (let e of c) e.reject(bt);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/*#__NO_SIDE_EFFECTS__*/
function St(e) {
	let t = /* @__PURE__ */ yt(e);
	return t.equals = We, t;
}
function Ct(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function wt(e) {
	var t, n = G, i = e.parent;
	if (!Bn && i !== null && e.v !== r && i.f & 24576) return Pe(), e.v;
	Hn(i);
	try {
		e.f &= ~se, Ct(e), t = $n(e);
	} finally {
		Hn(n);
	}
	return t;
}
function Tt(e) {
	var t = wt(e);
	if (!e.equals(t) && (e.wv = Xn(), (!j?.is_fork || e.deps === null) && (j === null ? e.v = t : (j.capture(e, t, !0), kt?.capture(e, t, !0)), e.deps === null))) {
		A(e, x);
		return;
	}
	Bn || (M === null ? nt(e) : (gn() || j?.is_fork) && M.set(e, t));
}
function Et(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && lt(() => {
		t.ac.abort(ye), t.ac = null;
	}), t.fn !== null && (t.teardown = _), tr(t, 0), kn(t));
}
function Dt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && nr(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var Ot = null, j = null, kt = null, M = null, At = null, jt = !1, Mt = !1, Nt = null, Pt = null, Ft = 0, It = 1, Lt = class e {
	id = It++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = 0;
	#o = /* @__PURE__ */ new Map();
	#s = null;
	#c = [];
	#l = [];
	#u = /* @__PURE__ */ new Set();
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Map();
	#p = /* @__PURE__ */ new Set();
	is_fork = !1;
	#m = !1;
	constructor() {
		Ot === null ? Ot = this : (Ot.#n = this, this.#t = Ot), Ot = this;
	}
	#h() {
		if (this.is_fork) return !0;
		for (let n of this.#o.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#f.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#f.has(e) || this.#f.set(e, {
			d: [],
			m: []
		}), this.#p.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#f.get(e);
		if (n) {
			this.#f.delete(e);
			for (var r of n.d) A(r, S), t(r);
			for (r of n.m) A(r, C), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		this.#e = !0, Ft++ > 1e3 && (this.#x(), zt());
		for (let e of this.#u) this.#d.delete(e), A(e, S), this.schedule(e);
		for (let e of this.#d) A(e, C), this.schedule(e);
		let t = this.#c;
		this.#c = [], this.apply();
		var n = Nt = [], r = [], i = Pt = [];
		for (let e of t) try {
			this.#_(e, n, r);
		} catch (t) {
			throw Wt(e), this.#h() || this.discard(), t;
		}
		if (j = null, i.length > 0) {
			var a = e.ensure();
			for (let e of i) a.schedule(e);
		}
		if (Nt = null, Pt = null, this.#h()) {
			this.#b(r), this.#b(n);
			for (let [e, t] of this.#f) Ut(e, t);
			i.length > 0 && j.#g();
			return;
		}
		let o = this.#v();
		if (o) {
			this.#b(r), this.#b(n), o.#y(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), kt = this, Vt(r), Vt(n), kt = null, this.#s?.resolve();
		var s = j;
		if (this.#a === 0 && (this.#c.length === 0 || s !== null) && this.#x(), this.#c.length > 0) {
			if (s !== null) {
				let e = s;
				e.#c.push(...this.#c.filter((t) => !e.#c.includes(t)));
			} else s = this;
		}
		s !== null && s.#g();
	}
	#_(e, t, n) {
		e.f ^= x;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#f.has(r)) && r.fn !== null) {
				a ? r.f ^= x : i & 4 ? t.push(r) : Zn(r) && (i & 16 && this.#d.add(r), nr(r));
				var o = r.first;
				if (o !== null) {
					r = o;
					continue;
				}
			}
			for (; r !== null;) {
				var s = r.next;
				if (s !== null) {
					r = s;
					break;
				}
				r = r.parent;
			}
		}
	}
	#v() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#y(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		e.async_deriveds.clear(), this.transfer_effects(e.#u, e.#d);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null && !(e.f & 2 && !(e.f & 6144))) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), A(i, S), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#x(), j = this, this.#g();
	}
	#b(e) {
		for (var t = 0; t < e.length; t += 1) it(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== r && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), M?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		j = this;
	}
	deactivate() {
		j = null, M = null;
	}
	flush() {
		try {
			Mt = !0, j = this, this.#g();
		} finally {
			Ft = 0, At = null, Nt = null, Pt = null, Mt = !1, j = null, M = null, Kt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(bt);
		this.#x(), this.#s?.resolve();
	}
	register_created_effect(e) {
		this.#l.push(e);
	}
	increment(e, t) {
		if (this.#a += 1, e) {
			let e = this.#o.get(t) ?? 0;
			this.#o.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#a, e) {
			let e = this.#o.get(t) ?? 0;
			e === 1 ? this.#o.delete(t) : this.#o.set(t, e - 1);
		}
		this.#m || (this.#m = !0, Ze(() => {
			this.#m = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#u.add(t);
		for (let e of t) this.#d.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	settled() {
		return (this.#s ??= b()).promise;
	}
	static ensure() {
		if (j === null) {
			let t = j = new e();
			!Mt && !jt && Ze(() => {
				t.#e || t.flush();
			});
		}
		return j;
	}
	apply() {
		M = null;
	}
	schedule(e) {
		if (At = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768)) {
			e.b.defer_effect(e);
			return;
		}
		for (var t = e; t.parent !== null;) {
			t = t.parent;
			var n = t.f;
			if (Nt !== null && t === G && (H === null || !(H.f & 2))) return;
			if (n & 96) {
				if (!(n & 1024)) return;
				t.f ^= x;
			}
		}
		this.#c.push(t);
	}
	#x() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null || (e.#n = t), t === null ? Ot = e : t.#t = e, this.linked = !1;
		}
	}
};
function Rt(e) {
	var t = jt;
	jt = !0;
	try {
		var n;
		for (e && (j !== null && !j.is_fork && j.flush(), n = e());;) {
			if (Qe(), j === null) return n;
			j.flush();
		}
	} finally {
		jt = t;
	}
}
function zt() {
	try {
		De();
	} catch (e) {
		et(e, At);
	}
}
var Bt = null;
function Vt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Zn(r) && (Bt = /* @__PURE__ */ new Set(), nr(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Mn(r), Bt?.size > 0)) {
				Kt.clear();
				for (let e of Bt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) Bt.has(n) && (Bt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || nr(n);
					}
				}
				Bt.clear();
			}
		}
		Bt = null;
	}
}
function Ht(e) {
	j.schedule(e);
}
function Ut(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), A(e, x);
		for (var n = e.first; n !== null;) Ut(n, t), n = n.next;
	}
}
function Wt(e) {
	A(e, x);
	for (var t = e.first; t !== null;) Wt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Gt = /* @__PURE__ */ new Set(), Kt = /* @__PURE__ */ new Map(), qt = !1;
function Jt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: He,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Yt(e, t) {
	let n = Jt(e, t);
	return Wn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function N(t, n = !1, r = !0) {
	let i = Jt(t);
	return n || (i.equals = We), e && r && k !== null && k.l !== null && (k.l.s ??= []).push(i), i;
}
function Xt(e, t) {
	return P(e, X(() => Y(e))), t;
}
function P(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && Je() && H.f & 4325394 && (Un === null || !Un.has(e)) && Me(), Zt(e, n ? tn(t) : t, Pt);
}
function Zt(e, t, n = null) {
	if (!e.equals(t)) {
		Kt.set(e, Bn ? t : e.v);
		var r = Lt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && wt(t), M === null && nt(t);
		}
		e.wv = Xn(), en(e, S, n), Je() && G !== null && G.f & 1024 && !(G.f & 96) && (J === null ? Gn([e]) : J.push(e)), !r.is_fork && Gt.size > 0 && !qt && Qt();
	}
	return t;
}
function Qt() {
	qt = !1;
	for (let e of Gt) {
		e.f & 1024 && A(e, C);
		let t;
		try {
			t = Zn(e);
		} catch {
			t = !0;
		}
		t && nr(e);
	}
	Gt.clear();
}
function $t(e) {
	P(e, e.v + 1);
}
function en(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Je(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & S) === 0;
			if (l && A(s, t), c & 131072) Gt.add(s);
			else if (c & 2) {
				var u = s;
				M?.delete(u), c & 65536 || (c & 512 && (G === null || !(G.f & 2097152)) && (s.f |= se), en(u, C, n));
			} else if (l) {
				var d = s;
				c & 16 && Bt !== null && Bt.add(d), n === null ? Ht(d) : n.push(d);
			}
		}
	}
}
function tn(e) {
	if (typeof e != "object" || !e || de in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ Yt(0), s = null, c = Jn, l = (e) => {
		if (Jn === c) return e();
		var t = H, n = Jn;
		W(null), Yn(c);
		var r = e();
		return W(t), Yn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ Yt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Ae();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Yt(r.value, s);
				return n.set(t, e), e;
			}) : P(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Yt(r, s));
					n.set(t, e), $t(o);
				}
			} else P(i, r), $t(o);
			return !0;
		},
		get(t, i, a) {
			if (i === de) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ Yt(tn(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = Y(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var i = Reflect.getOwnPropertyDescriptor(e, t);
			if (i && "value" in i) {
				var a = n.get(t);
				a && (i.value = Y(a));
			} else if (i === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== r) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return i;
		},
		has(e, t) {
			if (t === de) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || G !== null && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ Yt(a ? tn(e[t]) : r, s)), n.set(t, i)), Y(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Yt(r, s)), n.set(p + "", m)) : P(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Yt(void 0, s)), P(u, tn(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => tn(a));
				P(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && P(_, v + 1);
				}
				$t(o);
			}
			return !0;
		},
		ownKeys(e) {
			Y(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== r;
			});
			for (var [i, a] of n) a.v !== r && !(i in e) && t.push(i);
			return t;
		},
		setPrototypeOf() {
			je();
		}
	});
}
var nn, rn, an, on;
function sn() {
	if (nn === void 0) {
		nn = window, rn = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		an = d(t, "firstChild").get, on = d(t, "nextSibling").get, g(e) && (e[he] = void 0, e[me] = null, e[ge] = void 0, e.__e = void 0), g(n) && (n[_e] = void 0);
	}
}
function F(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function cn(e) {
	return an.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function I(e) {
	return on.call(e);
}
function L(e, t) {
	if (!T) return /* @__PURE__ */ cn(e);
	var n = /* @__PURE__ */ cn(E);
	if (n === null) n = E.appendChild(F());
	else if (t && n.nodeType !== 3) {
		var r = F();
		return n?.before(r), D(r), r;
	}
	return t && pn(n), D(n), n;
}
function ln(e, t = !1) {
	if (!T) {
		var n = /* @__PURE__ */ cn(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ I(n) : n;
	}
	if (t) {
		if (E?.nodeType !== 3) {
			var r = F();
			return E?.before(r), D(r), r;
		}
		pn(E);
	}
	return E;
}
function R(e, t = 1, n = !1) {
	let r = T ? E : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ I(r);
	if (!T) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = F();
			return r === null ? i?.after(a) : r.before(a), D(a), a;
		}
		pn(r);
	}
	return D(r), r;
}
function un(e) {
	e.textContent = "";
}
function dn() {
	return !1;
}
function fn(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function pn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function mn(e) {
	G === null && (H === null && Ee(e), Te()), Bn && we(e);
}
function hn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= w);
	var r = {
		ctx: k,
		deps: null,
		nodes: null,
		f: e | S | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	j?.register_created_effect(r);
	var i = r;
	if (e & 4) Nt === null ? Lt.ensure().schedule(r) : Nt.push(r);
	else if (t !== null) {
		try {
			nr(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= re));
	}
	if (i !== null && (i.parent = n, n !== null && hn(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function gn() {
	return H !== null && !U;
}
function _n(e) {
	let t = z(8, null);
	return A(t, x), t.teardown = e, t;
}
function vn(e) {
	mn("$effect");
	var t = G.f;
	if (!H && t & 32 && k !== null && !k.i) {
		var n = k;
		(n.e ??= []).push(e);
	} else return yn(e);
}
function yn(e) {
	return z(4 | ae, e);
}
function bn(e) {
	return mn("$effect.pre"), z(8 | ae, e);
}
function xn(e) {
	Lt.ensure();
	let t = z(64 | ie, e);
	return () => {
		V(t);
	};
}
function Sn(e) {
	Lt.ensure();
	let t = z(64 | ie, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Nn(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function Cn(e) {
	return z(4, e);
}
function wn(e) {
	return z(le | ie, e);
}
function Tn(e, t = 0) {
	return z(8 | t, e);
}
function En(e, t = [], n = [], r = []) {
	ht(r, t, n, (t) => {
		z(8, () => {
			e(...t.map(Y));
		});
	});
}
function Dn(e, t = 0) {
	return z(16 | t, e);
}
function B(e) {
	return z(32 | ie, e);
}
function On(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Bn, n = H;
		Vn(!0), W(null);
		try {
			t.call(null);
		} finally {
			Vn(e), W(n);
		}
	}
}
function kn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && lt(() => {
			e.abort(ye);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function An(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (jn(e.nodes.start, e.nodes.end), n = !0), e.f |= ne, kn(e, t && !n), tr(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	On(e), e.f ^= ne, e.f |= ee;
	var i = e.parent;
	i !== null && i.first !== null && Mn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function jn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ I(e);
		e.remove(), e = n;
	}
}
function Mn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Nn(e, t, n = !0) {
	var r = [];
	Pn(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Pn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= w;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				Pn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Fn(e) {
	In(e, !0);
}
function In(e, t) {
	if (e.f & 8192) {
		e.f ^= w, e.f & 1024 || (A(e, S), Lt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			In(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Ln(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ I(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Rn = null, zn = !1, Bn = !1;
function Vn(e) {
	Bn = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function Hn(e) {
	G = e;
}
var Un = null;
function Wn(e) {
	H !== null && (Un ??= /* @__PURE__ */ new Set()).add(e);
}
var K = null, q = 0, J = null;
function Gn(e) {
	J = e;
}
var Kn = 1, qn = 0, Jn = qn;
function Yn(e) {
	Jn = e;
}
function Xn() {
	return ++Kn;
}
function Zn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~se), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Zn(a) && Tt(a), a.wv > e.wv) return !0;
		}
		t & 512 && M === null && A(e, x);
	}
	return !1;
}
function Qn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(Un !== null && Un.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Qn(a, t, !1) : t === a && (n ? A(a, S) : a.f & 1024 && A(a, C), Ht(a));
	}
}
function $n(e) {
	var t = K, n = q, r = J, i = H, a = Un, o = k, s = U, c = Jn, l = e.f;
	K = null, q = 0, J = null, H = l & 96 ? null : e, Un = null, Ge(e.ctx), U = !1, Jn = ++qn, e.ac !== null && (lt(() => {
		e.ac.abort(ye);
	}), e.ac = null);
	try {
		e.f |= ce;
		var u = e.fn, d = u();
		e.f |= te;
		var f = e.deps, p = j?.is_fork;
		if (K !== null) {
			var m;
			if (p || tr(e, q), f !== null && q > 0) for (f.length = q + K.length, m = 0; m < K.length; m++) f[q + m] = K[m];
			else e.deps = f = K;
			if (gn() && e.f & 512) for (m = q; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && q < f.length && (tr(e, q), f.length = q);
		if (Je() && J !== null && !U && f !== null && !(e.f & 6146)) for (m = 0; m < J.length; m++) Qn(J[m], e);
		if (i !== null && i !== e) {
			if (qn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = qn;
			if (t !== null) for (let e of t) e.rv = qn;
			J !== null && (r === null ? r = J : r.push(...J));
		}
		return e.f & 8388608 && (e.f ^= ue), d;
	} catch (e) {
		return $e(e);
	} finally {
		e.f ^= ce, K = t, q = n, J = r, H = i, Un = a, Ge(o), U = s, Jn = c;
	}
}
function er(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (K === null || !s.call(K, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512, c.f &= ~se), c.v !== r && nt(c), c.ac !== null && lt(() => {
			c.ac.abort(ye), c.ac = null, A(c, S);
		}), Et(c), tr(c, 0);
	}
}
function tr(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) er(e, n[r]);
}
function nr(e) {
	var t = e.f;
	if (!(t & 16384)) {
		A(e, x);
		var n = G, r = zn;
		G = e, zn = !(t & 96);
		try {
			t & 16777232 ? An(e) : kn(e), On(e);
			var i = $n(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Kn;
		} finally {
			zn = r, G = n;
		}
	}
}
async function rr() {
	await Promise.resolve(), Rt();
}
function Y(e) {
	var t = !!(e.f & 2);
	if (Rn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (Un === null || !Un.has(e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < qn && (e.rv = qn, K === null && n !== null && n[q] === e ? q++ : K === null ? K = [e] : K.push(e));
		else {
			H.deps ??= [], s.call(H.deps, e) || H.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : s.call(r, H) || r.push(H);
		}
	}
	if (Bn && Kt.has(e)) return Kt.get(e);
	if (t) {
		var i = e;
		if (Bn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || ar(i)) && (a = wt(i)), Kt.set(i, a), a;
		}
		var o = !(i.f & 512) && !U && H !== null && (zn || !!(H.f & 512)), c = (i.f & te) === 0;
		Zn(i) && (o && (i.f |= 512), Tt(i)), o && !c && (Dt(i), ir(i));
	}
	if (M?.has(e)) return M.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function ir(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Dt(t), ir(t));
}
function ar(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Kt.has(t) || t.f & 2 && ar(t)) return !0;
	return !1;
}
function X(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function or(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (de in e) sr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && de in n && sr(n);
		}
	}
}
function sr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			sr(e[n], t);
		} catch {}
		let n = h(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = f(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var cr = Symbol("events"), lr = /* @__PURE__ */ new Set(), ur = /* @__PURE__ */ new Set();
function dr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || pr.call(t, e), !e.cancelBubble) return lt(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Ze(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = dr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && _n(() => {
		t.removeEventListener(e, o, a);
	});
}
var fr = null;
function pr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	fr = e;
	var o = 0, s = fr === e && e[cr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[cr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		u(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var d = H, f = G;
		W(null), Hn(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[cr]?.[r];
					h != null && (!a.disabled || e.target === a) && h.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble) break;
				o++, a = o < i.length ? i[o] : null;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[cr] = t, delete e.currentTarget, W(d), Hn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var mr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function hr(e) {
	return mr?.createHTML(e) ?? e;
}
function gr(e) {
	var t = fn("template");
	return t.innerHTML = hr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function _r(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (T) return _r(E, null), E;
		i === void 0 && (i = gr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ cn(i)));
		var t = r || rn ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ cn(t), s = t.lastChild;
			_r(o, s);
		} else _r(t, t);
		return t;
	};
}
function $(e, t) {
	if (T) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = E), Re();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var vr = ["touchstart", "touchmove"];
function yr(e) {
	return vr.includes(e);
}
function br(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[_e] ??= e.nodeValue) && (e[_e] = n, e.nodeValue = `${n}`);
}
function xr(e, t) {
	return wr(e, t);
}
function Sr(e, t) {
	sn(), t.intro = t.intro ?? !1;
	let r = t.target, i = T, a = E;
	try {
		for (var o = /* @__PURE__ */ cn(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ I(o);
		if (!o) throw n;
		Le(!0), D(o);
		let i = wr(e, {
			...t,
			anchor: o
		});
		return Le(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && Oe(), sn(), un(r), Le(!1), xr(e, t);
	} finally {
		Le(i), D(a);
	}
}
var Cr = /* @__PURE__ */ new Map();
function wr(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	sn();
	var u = void 0, d = Sn(() => {
		var s = r ?? t.appendChild(F());
		pt(s, { pending: () => {} }, (t) => {
			Ke({});
			var r = k;
			if (o && (r.c = o), a && (i.$$events = a), T && _r(t, null), u = e(t, i) || {}, T && (G.nodes.end = E, E === null || E.nodeType !== 8 || E.data !== "]")) throw Fe(), n;
			qe();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = yr(r);
					for (let e of [t, document]) {
						var a = Cr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), Cr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, pr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(lr)), ur.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = Cr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, pr), n.delete(e), n.size === 0 && Cr.delete(r)) : n.set(e, i);
			}
			ur.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return Tr.set(u, d), u;
}
var Tr = /* @__PURE__ */ new WeakMap();
function Er(e, t) {
	let n = Tr.get(e);
	return n ? (Tr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Dr = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) Fn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Fn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (V(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Ln(r, t), t.append(F()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Nn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = j, r = dn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = F();
				i.append(a), this.#n.set(e, {
					effect: B(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, B(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else T && (this.anchor = E), this.#a(n);
	}
};
function Or(t) {
	k === null && xe("onMount"), e && k.l !== null ? kr(k).m.push(t) : vn(() => {
		let e = X(t);
		if (typeof e == "function") return e;
	});
}
function kr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Ar(e, t, n = !1) {
	var r;
	T && (r = E, Re());
	var i = new Dr(e), a = n ? re : 0;
	function o(e, t) {
		if (T) {
			var n = Ve(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Be();
				D(a), i.anchor = a, Le(!1), i.ensure(e, t), Le(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Dn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function jr(e, t) {
	return t;
}
function Mr(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		Nn(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Nr(e, c(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var l = r.length === 0 && n !== null;
		if (l) {
			var u = n, d = u.parentNode;
			un(d), d.append(u), e.items.clear();
		}
		Nr(e, t, !l);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Nr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= oe, Ln(a, document.createDocumentFragment())) : V(t[i], n);
	}
}
var Pr;
function Fr(e, t, n, r, i, o = null) {
	var s = e, l = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = T ? D(/* @__PURE__ */ cn(u)) : u.appendChild(F());
	}
	T && Re();
	var d = null, f = /* @__PURE__ */ St(() => {
		var e = n();
		return a(e) ? e : e == null ? [] : c(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Lr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= oe, zr(d, null, s)) : Fn(d) : Nn(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: Dn(() => {
			p = Y(f);
			var e = p.length;
			let a = !1;
			T && Ve(s) === "[!" != (e === 0) && (s = Be(), D(s), Le(!1), a = !0);
			for (var c = /* @__PURE__ */ new Set(), u = j, v = dn(), y = 0; y < e; y += 1) {
				T && E.nodeType === 8 && E.data === "]" && (s = E, a = !0, Le(!1));
				var b = p[y], x = r(b, y), S = h ? null : l.get(x);
				S ? (S.v && Zt(S.v, b), S.i && Zt(S.i, y), v && u.unskip_effect(S.e)) : (S = Rr(l, h ? s : Pr ??= F(), b, x, y, i, t, n), h || (S.e.f |= oe), l.set(x, S)), c.add(x);
			}
			if (e === 0 && o && !d && (h ? d = B(() => o(s)) : (d = B(() => o(Pr ??= F())), d.f |= oe)), e > c.size && Ce("", "", ""), T && e > 0 && D(Be()), !h) {
				if (m.set(u, c), v) {
					for (let [e, t] of l) c.has(e) || u.skip_effect(t.e);
					u.oncommit(g), u.ondiscard(_);
				} else g(u);
			}
			a && Le(!0), Y(f);
		}),
		flags: t,
		items: l,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, T && (s = E);
}
function Ir(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Lr(e, t, n, r, i) {
	var a = !!(r & 8), o = t.length, s = e.items, l = Ir(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Fn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) {
			if (_.f ^= oe, _ === l) zr(_, null, n);
			else {
				var y = d ? d.next : l;
				_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Br(e, d, _), Br(e, _, y), zr(_, y, n), d = _, p = [], m = [], l = Ir(d.next);
				continue;
			}
		}
		if (_ !== l) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) zr(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Br(e, S.prev, C.next), Br(e, d, S), Br(e, C, b), l = b, d = C, --v, p = [], m = [];
				} else u.delete(_), zr(_, l, n), Br(e, _.prev, _.next), Br(e, _, d === null ? e.effect.first : d.next), Br(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; l !== null && l !== _;) (u ??= /* @__PURE__ */ new Set()).add(l), m.push(l), l = Ir(l.next);
			if (l === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, l = Ir(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Nr(e, c(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (l !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; l !== null;) !(l.f & 8192) && l !== e.fallback && w.push(l), l = Ir(l.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			Mr(e, w, te);
		}
	}
	a && Ze(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Rr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Jt(n) : /* @__PURE__ */ N(n, !1, !1) : null, l = o & 2 ? Jt(i) : null;
	return {
		v: c,
		i: l,
		e: B(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function zr(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ I(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Br(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Vr(e, t) {
	Cn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = fn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var Hr = [..." 	\n\r\f\xA0\v﻿"];
function Ur(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Hr.includes(r[o - 1])) && (s === r.length || Hr.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function Wr(e, t, n, r, i, a) {
	var o = e[he];
	if (T || o !== n || o === void 0) {
		var s = Ur(n, r, a);
		(!T || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[he] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Gr = Symbol("is custom element"), Kr = Symbol("is html"), qr = be ? "link" : "LINK";
function Jr(e) {
	if (T) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Yr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Yr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ve] = n, Ze(n), ct();
	}
}
function Yr(e, t, n, r) {
	var i = Xr(e);
	T && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === qr) || i[t] !== (i[t] = n) && (t === "loading" && (e[pe] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Qr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Xr(e) {
	return e[me] ??= {
		[Gr]: e.nodeName.includes("-"),
		[Kr]: e.namespaceURI === i
	};
}
var Zr = /* @__PURE__ */ new Map();
function Qr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Zr.get(t);
	if (n) return n;
	Zr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = h(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function $r(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	ut(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = ei(e) ? ti(a) : a, n(a), j !== null && r.add(j), await rr(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (T && e.defaultValue !== e.value || X(t) == null && e.value) && (n(ei(e) ? ti(e.value) : e.value), j !== null && r.add(j)), Tn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = j;
			if (r.has(i)) return;
		}
		ei(e) && n === ti(e.value) || e.type === "date" && !n && !e.value || n !== e.value && (e.value = n ?? "");
	});
}
function ei(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function ti(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function ni(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function ri(e = !1) {
	let t = k, n = t.l.u;
	if (!n) return;
	let r = () => or(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ yt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && bn(() => {
		ii(t, r), y(n.b);
	}), vn(() => {
		let e = X(() => n.m.map(v));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && vn(() => {
		ii(t, r), y(n.a);
	});
}
function ii(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/misc.js
function ai(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of a(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function oi(t, n, r, i) {
	var a = !e || !!(r & 2), o = !!(r & 8), s = !!(r & 16), c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ yt(i), Y(u)) : (l && (l = !1, c = s ? X(i) : i), c);
	let p;
	if (o) {
		var m = de in t || fe in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, g = !1;
	o ? [h, g] = ot(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && ke(n), p(h)));
	var _ = a ? () => {
		var e = t[n];
		return e === void 0 ? f() : (l = !0, e);
	} : () => {
		var e = t[n];
		return e !== void 0 && (c = void 0), e === void 0 ? c : e;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var v = t.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || v || g) && p(t ? _() : e), e) : _();
		});
	}
	var y = !1, b = (r & 1 ? yt : St)(() => (y = !1, _()));
	o && Y(b);
	var x = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(b) : a && o ? tn(e) : e;
			return P(b, n), y = !0, c !== void 0 && (c = n), e;
		}
		return Bn && y || x.f & 16384 ? b.v : Y(b);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function si(e) {
	return new ci(e);
}
var ci = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ N(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return Y(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === fe || (Y(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return P(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? Sr : xr)(e.component, {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		}), (!e?.props?.$$host || e.sync === !1) && Rt(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e !== "$set" && e !== "$destroy" && e !== "$on" && u(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			Er(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, li;
typeof HTMLElement == "function" && (li = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = fn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = di(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = ui(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = si({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = xn(() => {
				Tn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = ui(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = ui(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return l(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function ui(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function di(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function fi(e, t, n, r, i, a) {
	let o = class extends li {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return l(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return l(t).forEach((e) => {
		u(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = ui(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (d(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		u(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region TidalCard.svelte
var pi = /* @__PURE__ */ Q("<div class=\"loading-state svelte-11pw7by\">Loading...</div>"), mi = /* @__PURE__ */ Q("<div class=\"redirect-copy-group svelte-11pw7by\"><input type=\"text\" class=\"input-field readonly text-wrap svelte-11pw7by\" readonly=\"\"/> <button class=\"btn-primary copy-btn svelte-11pw7by\">Copy</button></div> <p class=\"helper-text svelte-11pw7by\">This auto-generated URI must be registered in your Tidal Developer Applications.</p>", 1), hi = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-11pw7by\">+ Add Account</button>"), gi = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-11pw7by\">✓ Authenticated</span>"), _i = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-11pw7by\">⚠ Not Authenticated</span>"), vi = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-11pw7by\">● Active</span>"), yi = /* @__PURE__ */ Q("<div class=\"account-item svelte-11pw7by\"><div class=\"account-info svelte-11pw7by\"><div class=\"account-name svelte-11pw7by\"> </div> <div class=\"account-badges svelte-11pw7by\"><!> <!></div></div> <div class=\"account-actions svelte-11pw7by\"><button class=\"link-btn svelte-11pw7by\">⚙️ Edit</button> <button class=\"link-btn svelte-11pw7by\"> </button> <button> </button> <button class=\"btn-danger svelte-11pw7by\">✕</button></div></div>"), bi = /* @__PURE__ */ Q("<div class=\"empty-accounts svelte-11pw7by\">No accounts added yet. Click \"Add Account\" to get started.</div>"), xi = /* @__PURE__ */ Q("<div class=\"settings-section svelte-11pw7by\"><div class=\"section-header svelte-11pw7by\"><h3 class=\"section-title svelte-11pw7by\">Global Redirect URI (Immutable)</h3> <button class=\"btn-ghost svelte-11pw7by\"> </button></div> <!></div> <div class=\"settings-section svelte-11pw7by\"><div class=\"section-header svelte-11pw7by\"><h3 class=\"section-title svelte-11pw7by\"> </h3> <!></div> <div class=\"accounts-list svelte-11pw7by\"></div></div>", 1), Si = /* @__PURE__ */ Q("<div class=\"modal-overlay svelte-11pw7by\"><div class=\"modal-content svelte-11pw7by\"><div class=\"modal-header svelte-11pw7by\"><h3 class=\"modal-title svelte-11pw7by\"> </h3> <button class=\"close-btn svelte-11pw7by\">✕</button></div> <div class=\"modal-body svelte-11pw7by\"><label class=\"form-field svelte-11pw7by\"><span class=\"field-label svelte-11pw7by\">Account Name</span> <input type=\"text\" placeholder=\"My Tidal Account\" class=\"input-field svelte-11pw7by\"/></label> <label class=\"form-field svelte-11pw7by\"><span class=\"field-label svelte-11pw7by\">Client ID</span> <input type=\"text\" placeholder=\"Enter Tidal Client ID\" class=\"input-field svelte-11pw7by\"/></label> <label class=\"form-field svelte-11pw7by\"><span class=\"field-label svelte-11pw7by\">Client Secret</span> <div class=\"password-wrapper svelte-11pw7by\"><input placeholder=\"Enter Tidal Client Secret\" class=\"input-field svelte-11pw7by\"/> <button type=\"button\" class=\"toggle-visibility svelte-11pw7by\"> </button></div></label></div> <div class=\"modal-footer svelte-11pw7by\"><button class=\"btn-ghost svelte-11pw7by\">Cancel</button> <button class=\"btn-primary svelte-11pw7by\"> </button></div></div></div>"), Ci = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-11pw7by\"><div class=\"card-header svelte-11pw7by\"><div class=\"header-left svelte-11pw7by\"><h2 class=\"card-title svelte-11pw7by\">Tidal</h2> <span class=\"type-badge svelte-11pw7by\">Streaming Service</span></div></div> <!></section> <!>", 1), wi = {
	hash: "svelte-11pw7by",
	code: ".plugin-card.svelte-11pw7by {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle);}.header-left.svelte-11pw7by {display:flex;align-items:center;gap:12px;}.card-title.svelte-11pw7by {margin:0;font-size:20px;font-weight:700;}.type-badge.svelte-11pw7by {font-size:11px;padding:4px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary);border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-11pw7by {padding:24px;text-align:center;color:var(--text-muted);}.settings-section.svelte-11pw7by {margin-bottom:24px;}.section-header.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}.section-title.svelte-11pw7by {margin:0;font-size:16px;font-weight:600;color:var(--text-primary);}.input-field.svelte-11pw7by {width:100%;padding:10px 14px;background:var(--bg-surface-elevated);border:1px solid var(--border-subtle);border-radius:8px;color:var(--text-primary);font-size:14px;transition:all 0.2s;}.input-field.svelte-11pw7by:focus {outline:none;border-color:var(--color-primary);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.input-field.readonly.svelte-11pw7by {opacity:0.6;cursor:not-allowed;}.helper-text.svelte-11pw7by {font-size:11px;color:var(--text-muted);margin-top:4px;}.redirect-copy-group.svelte-11pw7by {display:flex;gap:8px;align-items:stretch;}.redirect-copy-group.svelte-11pw7by .input-field:where(.svelte-11pw7by) {flex:1;font-family:monospace;overflow:hidden;text-overflow:ellipsis;}.text-wrap.svelte-11pw7by {word-break:break-all;white-space:normal;height:auto;min-height:40px;}.copy-btn.svelte-11pw7by {padding:0 16px;height:auto;white-space:nowrap;}.accounts-list.svelte-11pw7by {display:flex;flex-direction:column;gap:8px;}.account-item.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05);border-radius:8px;}.account-info.svelte-11pw7by {display:flex;flex-direction:column;gap:4px;}.account-name.svelte-11pw7by {font-weight:600;font-size:14px;}.account-badges.svelte-11pw7by {display:flex;gap:8px;}.status-badge.svelte-11pw7by {font-size:10px;padding:2px 6px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-11pw7by {background:rgba(34, 197, 94, 0.15);color:#22c55e;}.status-badge.warning.svelte-11pw7by {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-11pw7by {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.account-actions.svelte-11pw7by {display:flex;gap:12px;align-items:center;}.link-btn.svelte-11pw7by {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:600;cursor:pointer;}.link-btn.svelte-11pw7by:hover {text-decoration:underline;}.btn-ghost.svelte-11pw7by {padding:8px 16px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:var(--text-primary);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.svelte-11pw7by:hover {background:rgba(255,255,255,0.1);}.btn-primary.svelte-11pw7by {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-11pw7by:hover {opacity:0.9;}.btn-danger.svelte-11pw7by {background:rgba(239, 68, 68, 0.15);color:var(--color-danger);border:none;padding:8px 12px;border-radius:6px;cursor:pointer;}.modal-overlay.svelte-11pw7by {position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;backdrop-filter:blur(4px);}.modal-content.svelte-11pw7by {background:#0f1216;border:1px solid var(--border-subtle);border-radius:12px;width:100%;max-width:440px;box-shadow:0 24px 48px rgba(0,0,0,0.5);}.modal-header.svelte-11pw7by {padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;}.modal-title.svelte-11pw7by {margin:0;font-size:16px;font-weight:700;}.close-btn.svelte-11pw7by {background:none;border:none;color:var(--text-muted);font-size:20px;cursor:pointer;}.modal-body.svelte-11pw7by {padding:20px;display:flex;flex-direction:column;gap:16px;}.modal-footer.svelte-11pw7by {padding:16px 20px;border-top:1px solid rgba(255,255,255,0.05);display:flex;justify-content:flex-end;gap:12px;}.form-field.svelte-11pw7by {display:flex;flex-direction:column;gap:6px;}.field-label.svelte-11pw7by {font-size:13px;color:var(--text-muted);}.password-wrapper.svelte-11pw7by {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-11pw7by {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary);}.empty-accounts.svelte-11pw7by {text-align:center;padding:16px;color:var(--text-muted);font-size:13px;background:rgba(255,255,255,0.02);border-radius:8px;border:1px dashed rgba(255,255,255,0.1);}"
};
function Ti(e, t) {
	Ke(t, !1), Vr(e, wi);
	let n = oi(t, "apiBase", 12, ""), r = /* @__PURE__ */ N([]), i = /* @__PURE__ */ N(""), a = /* @__PURE__ */ N(!1), o = /* @__PURE__ */ N(!0), s = /* @__PURE__ */ N(!1), c = /* @__PURE__ */ N("add"), l = /* @__PURE__ */ N({
		id: null,
		account_name: "",
		client_id: "",
		client_secret: ""
	}), u = /* @__PURE__ */ N(!1), d = /* @__PURE__ */ N(!1);
	Or(async () => {
		await f(), P(a, !!Y(i)), P(o, !1);
	});
	async function f() {
		try {
			let e = await (await fetch(`${n()}`)).json();
			e && (P(r, e.accounts || []), P(i, e.redirect_uri || ""), P(a, !!Y(i)));
		} catch (e) {
			console.error("Failed to load Tidal accounts:", e);
		}
	}
	function p() {
		P(c, "add"), P(l, {
			id: null,
			account_name: "",
			client_id: "",
			client_secret: ""
		}), P(u, !0), P(d, !1), P(s, !0);
	}
	async function m(e) {
		P(c, "edit");
		try {
			let t = await (await fetch(`${n()}/${e.id}`)).json();
			t?.account && (P(l, {
				id: t.account.id,
				account_name: t.account.account_name,
				client_id: t.account.client_id || "",
				client_secret: t.account.client_secret || ""
			}), P(u, !1), P(d, !1), P(s, !0));
		} catch (e) {
			console.error("Failed to load account credentials:", e);
		}
	}
	function h() {
		P(s, !1), P(u, !1), P(d, !1), P(l, {
			id: null,
			account_name: "",
			client_id: "",
			client_secret: ""
		});
	}
	async function g() {
		if (!Y(l).account_name.trim() || !Y(l).client_id.trim()) {
			console.error("Account name and Client ID are required");
			return;
		}
		if (!Y(l).client_secret.trim()) {
			console.error("Client Secret is required");
			return;
		}
		try {
			let e = {
				account_name: Y(l).account_name,
				client_id: Y(l).client_id,
				client_secret: Y(l).client_secret
			};
			Y(c) === "add" ? await fetch(`${n()}`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}) : await fetch(`${n()}/${Y(l).id}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), h(), await f();
		} catch (e) {
			console.error("Failed to save account:", e);
		}
	}
	async function _(e, t) {
		try {
			await fetch(`${n()}/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), await f();
		} catch (e) {
			console.error("Failed to toggle account:", e);
		}
	}
	async function v(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			await fetch(`${n()}/${e}`, { method: "DELETE" }), await f();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function y(e) {
		try {
			let t = (await (await fetch(`${n()}/auth?account_id=${e}`)).json())?.auth_url;
			t ? window.location.href = t : console.error("Failed to get Tidal auth URL");
		} catch (e) {
			console.error("Failed to start OAuth:", e);
		}
	}
	var b = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Rt();
		}
	};
	ri();
	var x = Ci(), S = ln(x), C = R(L(S), 2), w = (e) => {
		$(e, pi());
	}, ee = (e) => {
		var t = xi(), n = ln(t), o = L(n), s = R(L(o), 2), c = L(s, !0);
		O(s), O(o);
		var l = R(o, 2), u = (e) => {
			var t = mi(), n = ln(t), r = L(n);
			Jr(r);
			var a = R(r, 2);
			O(n), ze(2), $r(r, () => Y(i), (e) => P(i, e)), Z("click", a, () => {
				navigator.clipboard.writeText(Y(i)), alert("Copied to clipboard!");
			}), $(e, t);
		};
		Ar(l, (e) => {
			Y(a) || e(u);
		}), O(n);
		var d = R(n, 2), f = L(d), h = L(f), g = L(h);
		O(h);
		var b = R(h, 2), x = (e) => {
			var t = hi();
			Z("click", t, p), $(e, t);
		};
		Ar(b, (e) => {
			Y(r), X(() => Y(r).length < 25) && e(x);
		}), O(f);
		var S = R(f, 2);
		Fr(S, 5, () => Y(r), jr, (e, t) => {
			var n = yi(), r = L(n), i = L(r), a = L(i, !0);
			O(i);
			var o = R(i, 2), s = L(o), c = (e) => {
				$(e, gi());
			}, l = (e) => {
				$(e, _i());
			};
			Ar(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = R(s, 2), d = (e) => {
				$(e, vi());
			};
			Ar(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			}), O(o), O(r);
			var f = R(r, 2), p = L(f), h = R(p, 2), g = L(h, !0);
			O(h);
			var b = R(h, 2);
			let x;
			var S = L(b, !0);
			O(b);
			var C = R(b, 2);
			O(f), O(n), En(() => {
				br(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), br(g, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), x = Wr(b, 1, "btn-ghost svelte-11pw7by", null, x, { active: Y(t).is_active }), br(S, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", p, () => m(Y(t))), Z("click", h, () => y(Y(t).id)), Z("click", b, () => _(Y(t).id, Y(t).is_active)), Z("click", C, () => v(Y(t).id, Y(t).display_name || Y(t).account_name)), $(e, n);
		}, (e) => {
			$(e, bi());
		}), O(S), O(d), En(() => {
			br(c, Y(a) ? "Expand" : "Collapse"), br(g, `Accounts (${Y(r), X(() => Y(r).length) ?? ""}/25)`);
		}), Z("click", s, () => P(a, !Y(a))), $(e, t);
	};
	Ar(C, (e) => {
		Y(o) ? e(w) : e(ee, -1);
	}), O(S);
	var te = R(S, 2), ne = (e) => {
		var n = Si(), r = L(n), i = L(r), a = L(i), o = L(a, !0);
		O(a);
		var s = R(a, 2);
		O(i);
		var f = R(i, 2), p = L(f), m = R(L(p), 2);
		Jr(m), O(p);
		var _ = R(p, 2), v = R(L(_), 2);
		Jr(v), O(_);
		var y = R(_, 2), b = R(L(y), 2), x = L(b);
		Jr(x);
		var S = R(x, 2), C = L(S, !0);
		O(S), O(b), O(y), O(f);
		var w = R(f, 2), ee = L(w), te = R(ee, 2), ne = L(te, !0);
		O(te), O(w), O(r), O(n), En(() => {
			br(o, Y(c) === "add" ? "Add Tidal Account" : "Edit Tidal Account"), Yr(x, "type", Y(d) ? "text" : "password"), br(C, Y(d) ? "🙈" : "👁️"), br(ne, Y(c) === "add" ? "Add Account" : "Save Changes");
		}), Z("click", s, h), $r(m, () => Y(l).account_name, (e) => Xt(l, Y(l).account_name = e)), $r(v, () => Y(l).client_id, (e) => Xt(l, Y(l).client_id = e)), $r(x, () => Y(l).client_secret, (e) => Xt(l, Y(l).client_secret = e)), Z("input", x, () => P(u, !0)), Z("click", S, () => P(d, !Y(d))), Z("click", ee, h), Z("click", te, g), Z("click", r, ni(function(e) {
			ai.call(this, t, e);
		})), Z("click", n, h), $(e, n);
	};
	return Ar(te, (e) => {
		Y(s) && e(ne);
	}), $(e, x), qe(b);
}
customElements.define("tidal-dashboard-card", fi(Ti, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { Ti as default };
